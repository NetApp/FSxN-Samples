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
