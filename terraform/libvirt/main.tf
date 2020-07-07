
locals {
    node_volume_name       = var.node_source_image != "" ? "" : (var.node_volume_name != "" ? var.node_volume_name : local.base_volume_name)
    iscsi_volume_name      = var.iscsi_source_image != "" ? "" : (var.iscsi_volume_name != "" ? var.iscsi_volume_name : local.base_volume_name)
    monitor_volume_name    = var.monitor_source_image != "" ? "" : (var.monitor_volume_name != "" ? var.monitor_volume_name : local.base_volume_name)

    iscsi_private_ip       = cidrhost(var.private_ip_range, 4)
    monitor_private_ip     = cidrhost(var.private_ip_range, 5)
    node_private_ips_start = 10
    node_private_ips       = [for ip_index in range(local.node_private_ips_start, local.node_private_ips_start + var.node_count) : cidrhost(var.private_ip_range, ip_index)]
}

module "node" {
    source               = "./modules/node"
    name                 = "node"
    source_image         = var.node_source_image
    volume_name          = local.node_volume_name
    storage_pool         = var.storage_pool
    node_count           = var.node_count
    cpus                 = var.node_cpus
    memory               = var.node_memory
    disk_size            = var.node_disk_size
    public_bridge        = var.public_bridge
    public_network_id    = local.public_network_id
    private_network_id   = local.private_network_id
    node_private_ips     = local.node_private_ips
    shared_storage_type  = var.shared_storage_type
    sbd_disk_id          = module.sbd_disk.id
}

module "iscsi" {
    source                = "./modules/iscsi"
    source_image          = var.iscsi_source_image
    volume_name           = local.iscsi_volume_name
    storage_pool          = var.storage_pool
    iscsi_enabled         = var.shared_storage_type == "iscsi"
    cpus                  = var.iscsi_cpus
    memory                = var.iscsi_memory
    disk_size             = var.iscsi_disk_size
    iscsi_dev             = "/dev/vdb"
    public_bridge         = var.public_bridge
    public_network_id     = local.public_network_id
    private_network_id    = local.private_network_id
    iscsi_private_ip      = local.iscsi_private_ip
}

module "monitor" {
    source                = "./modules/monitor"
    name                  = "monitor"
    source_image          = var.monitor_source_image
    volume_name           = local.monitor_volume_name
    storage_pool          = var.storage_pool
    monitor_enabled       = var.monitor_enabled
    cpus                  = var.monitor_cpus
    memory                = var.monitor_memory
    public_bridge         = var.public_bridge
    public_network_id     = local.public_network_id
    private_network_id    = local.private_network_id
    monitor_private_ip    = local.monitor_private_ip
}
