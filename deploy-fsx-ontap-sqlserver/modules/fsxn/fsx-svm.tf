resource "aws_fsx_ontap_storage_virtual_machine" "fsxsvm01" {
  file_system_id             = aws_fsx_ontap_file_system.fsx_ontap_fs.id
  name                       = "svm01"
  root_volume_security_style = var.fsxn_volume_security_style
  svm_admin_password         = var.fsxn_password
}
