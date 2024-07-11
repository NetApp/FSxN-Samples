variable "fsxn_password" {
  description = "Default Password"
  type        = string
  sensitive   = true
}

variable "fsxn_volume_security_style" {
  description = "Default Volume Security Style"
  type        = string
  default     = "NTFS"

  validation {
    condition     = contains(["NTFS", "UNIX"], var.fsxn_volume_security_style)
    error_message = "Invalid Security Style. Valid values are NTFS and UNIX."
  }
}

variable "fsxn_subnet_ids" {
  description = "FSxN Deployment Subnet ID"
  type        = list(string)
}

variable "fsxn_security_group_ids" {
  description = "FSxN Security Groups IDs"
  type        = list(string)
}

variable "fsxn_throughput_capacity" {
  description = "FSxN Throughput Capacity (128, 256, 512, 1024, 2048)"
  type        = number
  default     = 128

  validation {
    condition     = contains([128, 256, 512, 1024, 2048], var.fsxn_throughput_capacity)
    error_message = "Invalid Throughput Capacity. Valid values are 128, 256, 512, 1024, 2048."
  }
}

variable "fsxn_ssd_in_gb" {
  description = "FSxN SSD Size in GB"
  type        = number
  default     = 1024

  validation {
    condition = (
      var.fsxn_ssd_in_gb >= 1024 &&
      var.fsxn_ssd_in_gb <= 196608
    )
    error_message = "Must be between 1024 and 196608 GB, inclusive."
  }
}

variable "creator_tag" {
  description = "Value of the creator tag"
  type        = string
}

variable "fsxn_volume_name_prefix" {
  description = "Prefix to identify the volume name with the sql instance or server"
  type        = string
}

variable "fsxn_deployment_type" {
  description = "FSxN Deployment Type - Multi-AZ or Single AZ"
  type        = string
  default     = "SINGLE_AZ_1"

  validation {
    condition     = contains(["SINGLE_AZ_1", "MULTI_AZ_1"], var.fsxn_deployment_type)
    error_message = "Invalid Deployment Type - Valid values are SINGLE_AZ_1 or MULTI_AZ_1."
  }
}
