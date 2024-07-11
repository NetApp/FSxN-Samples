output "FSxN_management_ip" {
  description = "FSxN Management IP"
  value       = module.fsxontap.fsx_management_management_ip
}

output "FSxN_svm_iscsi_endpoints" {
  description = "FSxN SVM iSCSI endpoints"
  value       = module.fsxontap.fsx_svm_iscsi_endpoints
}

output "FSxN_sql_server_ip" {
  description = "FSxN SQL Serer Private and Public IP addresses"
  value       = module.sqlserver.ip_address
}

output "FSxN_file_system_id" {
  value = module.fsxontap.fsx_file_system.id
}

output "FSxN_svm_id" {
  value = module.fsxontap.fsx_svm.id
}

output "FSxN_sql_data_volume" {
  value = {
    id   = module.fsxontap.fsx_sql_data_volume.id
    name = module.fsxontap.fsx_sql_data_volume.name
  }
}

output "FSxN_sql_log_volume" {
  value = {
    id   = module.fsxontap.fsx_sql_log_volume.id
    name = module.fsxontap.fsx_sql_log_volume.name
  }
}

output "instance_id" {
  description = "The ID of the EC2 instance"
  value       = module.sqlserver.id
}

output "public_ip" {
  description = "The public IP address of the EC2 instance"
  value       = module.sqlserver.public_ip
}

output "private_ip" {
  description = "The private IP address of the EC2 instance"
  value       = module.sqlserver.private_ip
}

output "hostname" {
  description = "The public DNS name of the EC2 instance"
  value       = module.sqlserver.public_dns
}

output "username" {
  description = "The username of the EC2 instance"
  value       = "Administrator"
}

output "password" {
  description = "The password of the EC2 instance"
  value       = random_password.password.result
  sensitive   = false
}
