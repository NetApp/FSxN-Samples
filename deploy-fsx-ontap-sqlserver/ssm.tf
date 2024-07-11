resource "aws_ssm_parameter" "fsxpassword" {
  name        = "/fsxn/password/fsxadmin"
  description = "FSxN Admin Password"
  type        = "SecureString"
  value       = var.fsxn_password

  tags = {
    creator = var.creator_tag
  }
}
