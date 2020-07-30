output "node_private_ips" {
    value = length(module.node.output_data.public_ips) != 0 ? module.node.output_data.private_ips : []
}

output "node_public_ips" {
    value = module.node.output_data.public_ips
}

output "node_names" {
    value = module.node.output_data.hostnames
}

output "iscsi_private_ip" {
    value = module.iscsi.output_data.public_ip != "" ? module.iscsi.output_data.private_ip : ""
}

output "iscsi_public_ip" {
    value = module.iscsi.output_data.public_ip
}

output "iscsi_name" {
    value = module.iscsi.output_data.hostname
}

output "qdevice_private_ip" {
    value = module.qdevice.output_data.public_ip != "" ? module.qdevice.output_data.private_ip : ""
}

output "qdevice_public_ip" {
    value = module.qdevice.output_data.public_ip
}

output "qdevice_name" {
    value = module.qdevice.output_data.hostname
}
