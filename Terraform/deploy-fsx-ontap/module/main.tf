# Copyright (c) NetApp, Inc.
# SPDX-License-Identifier: Apache-2.0

/*
   The following resources are for deploying a complete FSx ONTAP file system. 
   The code below deploys the following resources in this order:
   1. A file system 
   2. A storage virtual machine
   3. A volume within the storage virtual machine
  
   Every resource include both optional and required parameters, separated by a comment line.
   Feel free to add or remove optional parameters as needed.
 */

resource "aws_fsx_ontap_file_system" "terraform-fsxn" {
  // REQUIRED PARAMETERS 
  subnet_ids = (var.deployment_type == "MULTI_AZ_1" ? [var.subnets["primarysub"], var.subnets["secondarysub"]] : [var.subnets["primarysub"]])
  preferred_subnet_id = var.subnets["primarysub"]

  // OPTIONAL PARAMETERS
  storage_capacity                  = var.capacity_size_gb
  security_group_ids                = var.create_sg ? [element(aws_security_group.fsx_sg[*].id, 0)] : [var.security_group_id]
  deployment_type                   = var.deployment_type
  throughput_capacity               = var.throughput_in_MBps
  weekly_maintenance_start_time     = var.maintenance_start_time
  kms_key_id                        = var.kms_key_id
  automatic_backup_retention_days   = var.backup_retention_days
  daily_automatic_backup_start_time = var.daily_backup_start_time
  route_table_ids                   = (var.deployment_type == "MULTI_AZ_1" ? var.route_table_ids : null)
  tags                              = merge(var.tags, {Name = var.name })
  dynamic "disk_iops_configuration" {
    for_each = length(var.disk_iops_configuration) > 0 ? [var.disk_iops_configuration] : []

    content {
      iops = try(disk_iops_configuration.value.iops, null)
      mode = try(disk_iops_configuration.value.mode, null)
    }
  }

  lifecycle {
    precondition {
      condition = !var.create_sg || (var.cidr_for_sg != "" && var.source_sg_id == "" || var.cidr_for_sg == "" && var.source_sg_id != "")
      error_message = "You must specify EITHER cidr_block OR source_sg_id when creating a security group, not both."
    }
    precondition {
      condition = var.create_sg || var.security_group_id != ""
      error_message = "You must specify a security group ID when not creating a security group."
    }
  }
}

data "aws_region" "current" {}

#
# Instantiate a secret for the FSx ONTAP file system. It will set the initial password for the file system.
module "fsxn_rotate_secret" {
    source = "github.com/Netapp/FSx-ONTAP-samples-scripts/Management-Utilities/fsxn-rotate-secret/terraform"
    fsx_region = data.aws_region.current.name
    secret_region = var.secrets_region != "" ? var.secrets_region : data.aws_region.current.name
    aws_account_id = var.aws_account_id
    secret_name_prefix = var.secret_name_prefix
    fsx_id = aws_fsx_ontap_file_system.terraform-fsxn.id
}

resource "aws_fsx_ontap_storage_virtual_machine" "mysvm" {
  // REQUIRED PARAMETERS
  file_system_id = aws_fsx_ontap_file_system.terraform-fsxn.id
  name           = var.svm_name

  // OPTIONAL PARAMETERS
  root_volume_security_style = var.root_vol_sec_style
}
#
# Instantiate a secret for the FSx ONTAP file system. It will set the initial password for the SVM.
module "svm_rotate_secret" {
    source = "github.com/Netapp/FSx-ONTAP-samples-scripts/Management-Utilities/fsxn-rotate-secret/terraform"
    fsx_region = data.aws_region.current.name
    secret_region = var.secrets_region != "" ? var.secrets_region : data.aws_region.current.name
    aws_account_id = var.aws_account_id
    secret_name_prefix = var.secret_name_prefix
    svm_id = aws_fsx_ontap_storage_virtual_machine.mysvm.id
}

resource "aws_fsx_ontap_volume" "myvol" {
  // REQUIRED PARAMETERS
  name                       = var.vol_info["vol_name"]
  size_in_megabytes          = var.vol_info["size_mg"]
  storage_virtual_machine_id = aws_fsx_ontap_storage_virtual_machine.mysvm.id

  // OPTIONAL PARAMETERS
  junction_path              = var.vol_info["junction_path"]
  ontap_volume_type          = var.vol_info["vol_type"]
  storage_efficiency_enabled = var.vol_info["efficiency"]
  tiering_policy {
    name           = var.vol_info["tier_policy_name"]
    cooling_period = var.vol_info["cooling_period"]
  }
  copy_tags_to_backups       = var.vol_info["copy_tags_to_backups"]
  security_style             = var.vol_info["sec_style"]
  skip_final_backup          = var.vol_info["skip_final_backup"]
  snapshot_policy            = var.vol_info["snapshot_policy"]
}
