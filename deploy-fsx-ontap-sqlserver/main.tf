terraform {

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "5.25.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "2.5.1"
    }
  }

}

provider "random" {}

provider "aws" {
  region = var.aws_location

  default_tags {
    tags = {
      "creator" = var.creator_tag
    }
  }
}

locals {
  ec2_name = "${var.creator_tag}_SQL_${var.environment}"
}

resource "random_password" "password" {
  length           = 16
  special          = true
  override_special = "_%@"
}

module "fsxontap" {
  source = "./modules/fsxn"

  fsxn_password           = var.fsxn_password
  fsxn_deployment_type    = "SINGLE_AZ_1"
  fsxn_subnet_ids         = [aws_subnet.private_subnet[0].id, aws_subnet.private_subnet[1].id]
  fsxn_security_group_ids = [aws_security_group.sg-fsx.id]
  fsxn_volume_name_prefix = local.ec2_name

  creator_tag = var.creator_tag
}

module "sqlserver" {
  source = "./modules/ec2"

  ec2_instance_name       = local.ec2_name
  ec2_instance_type       = var.ec2_instance_type
  ec2_instance_key_pair   = var.ec2_instance_keypair
  ec2_iam_role            = var.ec2_iam_role
  ec2_subnet_id           = aws_subnet.public_subnet[0].id
  ec2_security_groups_ids = [aws_security_group.sg-fsx.id, aws_security_group.sg-AllowRemoteToEC2.id]
  admin_password          = random_password.password.result

  fsxn_password        = var.fsxn_password
  fsxn_iscsi_ips       = module.fsxontap.fsx_svm_iscsi_endpoints
  fsxn_svm             = module.fsxontap.fsx_svm.name
  fsxn_management_ip   = module.fsxontap.fsx_management_management_ip
  fsxn_sql_data_volume = module.fsxontap.fsx_sql_data_volume
  fsxn_sql_log_volume  = module.fsxontap.fsx_sql_log_volume

  sql_data_volume_drive_letter = "D"
  sql_log_volume_drive_letter  = "E"
  sql_install_sample_database  = true

  creator_tag = var.creator_tag
  depends_on  = [module.fsxontap]
}
