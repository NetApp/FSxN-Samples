variable "ec2_instance_type" {
  description = "EC2 Instance Type for SQL Server"
  type        = string
  default     = "t3.2xlarge"
}

variable "ec2_instance_name" {
  description = "EC2 Instance Name"
  type        = string
}

variable "ec2_instance_key_pair" {
  description = "EC2 Instance Key Pair Name"
  type        = string
}

variable "ec2_iam_role" {
  description = "EC2 IAM Role with access to SSM Parameters"
  type        = string
}

variable "fsxn_admin_user" {
  description = "FSxN Admin User"
  type        = string
  default     = "fsxadmin"
}

variable "fsxn_password" {
  description = "FSxN Admin Passowrd"
  type        = string
  sensitive   = true
}

variable "fsxn_svm" {
  description = "FSxN SVM"
  type        = string
  default     = "svm01"
}

variable "fsxn_sql_log_volume" {
  description = "FSxN SQL Data Volume"
}

variable "fsxn_sql_data_volume" {
  description = "FSxN SQL Log Volume"
}

variable "fsxn_management_ip" {
  description = "FSxN Management IP"
  type        = list(string)
}

variable "ec2_subnet_id" {
  description = "Subnet Id for EC2 Instance"
  type        = string
}

variable "sql_data_volume_drive_letter" {
  description = "SQL Data Volume Drive Letter"
  type        = string

  validation {
    condition     = can(regex("^[D-Z]{1}$", var.sql_data_volume_drive_letter))
    error_message = "Must be single letter between D and Z."
  }
}

variable "sql_log_volume_drive_letter" {
  description = "SQL Log Volume Drive Letter"
  type        = string

  validation {
    condition     = can(regex("^[D-Z]{1}$", var.sql_log_volume_drive_letter))
    error_message = "Must be single letter between D and Z."
  }
}

variable "sql_install_sample_database" {
  description = "Install Sample StackOverflow Database"
  type        = bool
  default     = false
}

variable "ec2_security_groups_ids" {
  description = "Security Groups for EC2 Instance"
  type        = list(string)
}

variable "creator_tag" {
  description = "Tag with the Key as Creator"
  type        = string
}

variable "fsxn_iscsi_ips" {
  description = "IP Address of the FSxN SVM iSCSI Protocol"
  type        = list(string)
}

variable "admin_password" {
  description = "The password for the Administrator user"
  type        = string
}
