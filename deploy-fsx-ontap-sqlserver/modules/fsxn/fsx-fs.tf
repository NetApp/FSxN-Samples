resource "aws_fsx_ontap_file_system" "fsx_ontap_fs" {
  storage_capacity    = var.fsxn_ssd_in_gb
  throughput_capacity = var.fsxn_throughput_capacity
  deployment_type     = var.fsxn_deployment_type
  /* 
    Use Single Subnet if the Deployment Type is Single AZ. 
  */
  subnet_ids          = (var.fsxn_deployment_type == "SINGLE_AZ_1") ? [var.fsxn_subnet_ids[0]] : var.fsxn_subnet_ids
  preferred_subnet_id = var.fsxn_subnet_ids[0]
  fsx_admin_password  = var.fsxn_password
  security_group_ids  = var.fsxn_security_group_ids

  tags = {
    "Name" = "${var.creator_tag}-FSxN-SQL-Demo"
  }
}



