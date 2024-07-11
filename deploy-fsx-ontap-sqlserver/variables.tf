
variable "creator_tag" {
  description = "Value of the creator tag"
  type        = string
}

variable "aws_location" {
  description = "Value of the location"
  type        = string
  default     = "ap-southeast-1"

  validation {
    condition     = can(regex("[a-z][a-z]-[a-z]+-[1-9]", var.aws_location))
    error_message = "Must be valid AWS Region names."
  }
}

variable "ec2_iam_role" {
  description = "Value of the EC2 IAM Role"
  type        = string
}

variable "ec2_instance_type" {
  description = "Value of the instance type"
  type        = string
}

variable "ec2_instance_keypair" {
  description = "Value of the instance key pair"
  type        = string
}

variable "fsxn_password" {
  description = "Default Password"
  type        = string
  sensitive   = true
}

variable "volume_security_style" {
  description = "Default Volume Security Style"
  type        = string
  default     = "NTFS"
}

variable "environment" {
  description = "Deployment Environment"
  default     = "Demo"
}

variable "vpc_cidr" {
  description = "CIDR block of the vpc"
  default     = "10.0.0.0/16"
}

variable "public_subnets_cidr" {
  type        = list(any)
  description = "CIDR block for Public Subnet"
  default     = ["10.0.0.0/20", "10.0.16.0/20"]
}

variable "private_subnets_cidr" {
  type        = list(any)
  description = "CIDR block for Private Subnet"
  default     = ["10.0.128.0/20", "10.0.144.0/20"]
}

variable "availability_zones" {
  type        = list(any)
  description = "AZ in which all the resources will be deployed"
  default     = ["ap-southeast-1a", "ap-southeast-1b"]
}


variable "ec2_security_group_config" {
  default = [
    {
      description      = "RDP Port"
      port             = 3389
      protocol         = "tcp"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "SSH Port"
      port             = 22
      protocol         = "tcp"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    }
  ]
}

variable "fsx_security_group_ingress_config" {
  default = [
    {
      description      = "All Ports"
      port             = 0
      protocol         = "-1"
      cidr_blocks      = ["10.0.0.0/16"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "All Ports"
      port             = 0
      protocol         = "-1"
      cidr_blocks      = ["10.0.0.0/16"]
      ipv6_cidr_blocks = ["::/0"]
    }
  ]
}

variable "fsx_security_group_egress_config" {
  default = [
    {
      description      = "Remote procedure call for NFS"
      port             = 111
      protocol         = "TCP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "Remote procedure call for CIFS"
      port             = 135
      protocol         = "TCP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "Simple network management protocol (SNMP)"
      port             = 161
      protocol         = "TCP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "Simple network management protocol (SNMP)"
      port             = 162
      protocol         = "TCP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "ONTAP REST API access to the IP address of the cluster management LIF or an SVM management LIF"
      port             = 443
      protocol         = "TCP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "Microsoft SMB/CIFS over TCP with NetBIOS framing"
      port             = 445
      protocol         = "TCP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "NFS mount"
      port             = 635
      protocol         = "TCP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "Kerberos"
      port             = 749
      protocol         = "TCP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "NFS Server Daemon"
      port             = 2049
      protocol         = "TCP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "iSCSI access through the iSCSI data LIF"
      port             = 3260
      protocol         = "TCP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "NFS Lock Daemon"
      port             = 4045
      protocol         = "TCP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "Network status monitor for NFS"
      port             = 4046
      protocol         = "TCP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "Network data management protocol (NDMP) and NetApp SnapMirror intercluster communication"
      port             = 10000
      protocol         = "TCP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "Management of NetApp SnapMirror intercluster communication"
      port             = 11104
      protocol         = "TCP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "SnapMirror data transfer using intercluster LIFs"
      port             = 11105
      protocol         = "TCP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "Remote procedure call for NFS"
      port             = 111
      protocol         = "UDP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "Remote procedure call for CIFS"
      port             = 135
      protocol         = "UDP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "NetBIOS name resolution for CIFS"
      port             = 137
      protocol         = "UDP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "NetBIOS service session for CIFS"
      port             = 139
      protocol         = "UDP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "Simple network management protocol (SNMP)"
      port             = 161
      protocol         = "UDP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "Simple network management protocol (SNMP)"
      port             = 162
      protocol         = "UDP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "NFS Mount"
      port             = 635
      protocol         = "UDP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "NFS server daemon"
      port             = 2049
      protocol         = "UDP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "NFS Lock Daemon"
      port             = 4045
      protocol         = "UDP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },
    {
      description      = "Network status monitor for NFS"
      port             = 4046
      protocol         = "UDP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    },

    {
      description      = "NFS quota protocol"
      port             = 4049
      protocol         = "TCP"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = ["::/0"]
    }
  ]
}
