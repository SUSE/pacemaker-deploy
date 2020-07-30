provider "libvirt" {
    uri = var.qemu_uri
}

locals {
    base_volume_name       = var.source_image != "" ? libvirt_volume.base_image.0.name : var.volume_name != "" ? var.volume_name : ""
    node_volume_name       = var.node_source_image != "" ? "" : (var.node_volume_name != "" ? var.node_volume_name : local.base_volume_name)
    iscsi_volume_name      = var.iscsi_source_image != "" ? "" : (var.iscsi_volume_name != "" ? var.iscsi_volume_name : local.base_volume_name)
    qdevice_volume_name    = var.qdevice_source_image != "" ? "" : (var.qdevice_volume_name != "" ? var.qdevice_volume_name : local.base_volume_name)

    iscsi_private_ip       = cidrhost(var.private_ip_range, 4)
    qdevice_private_ip     = cidrhost(var.private_ip_range, 6)
    node_private_ips_start = 10
    node_private_ips       = [for ip_index in range(local.node_private_ips_start, local.node_private_ips_start + var.node_count) : cidrhost(var.private_ip_range, ip_index)]

    public_network_id    = var.public_bridge == "" && var.public_ip_range != "" ? libvirt_network.public_network.0.id : ""
    private_network_id   = libvirt_network.private_network.0.id
}

#
# Images
#
resource "libvirt_volume" "base_image" {
    count  = var.source_image != "" ? 1 : 0
    name   = "${terraform.workspace}-base-image"
    pool   = var.storage_pool
    source = var.source_image
}

#
# Networks
#
resource "libvirt_network" "public_network" {
    count     = var.public_bridge == "" && var.public_ip_range != "" ? 1 : 0
    name      = "${terraform.workspace}-public"
    bridge    = "${terraform.workspace}-pb-br"
    mode      = "nat"
    addresses = [var.public_ip_range]
    dhcp {
        enabled = "true"
    }
    dns {
        enabled = true
    }
    autostart = true
}

resource "libvirt_network" "private_network" {
    count     = 1
    name      = "${terraform.workspace}-private"
    bridge    = "${terraform.workspace}-pr-br"
    mode      = "none"
    addresses = [var.private_ip_range]
    dhcp {
        enabled = "false"
    }
    dns {
        enabled = true
    }
    autostart = true
}


#
# Modules
#
module "node" {
    source               = "./modules/node"
    node_count           = var.node_count
    storage_pool         = var.storage_pool
    source_image         = var.node_source_image
    volume_name          = local.node_volume_name
    cpus                 = var.node_cpus
    memory               = var.node_memory
    disk_size            = var.node_disk_size
    public_bridge        = var.public_bridge
    public_network_id    = local.public_network_id
    private_network_id   = local.private_network_id
    node_private_ips     = local.node_private_ips
    sbd_disk_id          = module.sbd_disk.id
}

module "sbd_disk" {
    source        = "./modules/shared_disk"
    enabled       = var.shared_storage_type == "shared-disk"
    storage_pool  = var.storage_pool
    disk_size     = var.sbd_disk_size
}

module "iscsi" {
    source                = "./modules/iscsi"
    enabled               = var.shared_storage_type == "iscsi"
    storage_pool          = var.storage_pool
    source_image          = var.iscsi_source_image
    volume_name           = local.iscsi_volume_name
    cpus                  = var.iscsi_cpus
    memory                = var.iscsi_memory
    disk_size             = var.iscsi_disk_size
    public_bridge         = var.public_bridge
    public_network_id     = local.public_network_id
    private_network_id    = local.private_network_id
    iscsi_private_ip      = local.iscsi_private_ip
}

module "qdevice" {
    source                = "./modules/qdevice"
    enabled               = var.qdevice_enabled
    storage_pool          = var.storage_pool
    source_image          = var.qdevice_source_image
    volume_name           = local.qdevice_volume_name
    public_bridge         = var.public_bridge
    public_network_id     = local.public_network_id
    private_network_id    = local.private_network_id
    qdevice_private_ip    = local.qdevice_private_ip
}
