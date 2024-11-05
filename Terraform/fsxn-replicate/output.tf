#output "volume_details" {
#  value = {
#    for key, volume in data.netapp-ontap_storage_volume_data_source.src_vols : key => {
#      name      = volume.name
#      type      = volume.type
#      size      = "${volume.space.size}${volume.space.size_unit}"
#    }
#  }
#  description = "Details of the volumes including name, type, size, and size unit"
#}

#output "data_from_aws_fsxn" {
#  value =  {
#      all_of_it = data.aws_fsx_ontap_file_system.source_fsxn
#  }
#  description = "All data from aws fsxn provider"
#}


output "dr_fsxn_system" {
  value =  {
      cluster_mgmt_ip = aws_fsx_ontap_file_system.terraform-fsxn.endpoints[0].management[0].ip_addresses
  }
  description = "Cluster management IP address of the created DR cluster"
}
