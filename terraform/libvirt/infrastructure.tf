provider "libvirt" {
    uri = var.qemu_uri
}

locals {
    internal_network_name = var.network_name
    internal_network_id   = var.network_name != "" ? "" : libvirt_network.isolated_network.0.id
    base_volume_name      = var.source_image != "" ? libvirt_volume.base_image.0.name : var.volume_name != "" ? var.volume_name : ""
    ip_range              = var.ip_range
}

resource "libvirt_volume" "base_image" {
    count  = var.source_image != "" ? 1 : 0
    name   = "${terraform.workspace}-baseimage"
    source = var.source_image
    pool   = var.storage_pool
}

#
# Internal network
#
resource "libvirt_network" "isolated_network" {
    count     = var.network_name == "" ? 1 : 0
    name      = "${terraform.workspace}-network"
    bridge    = var.isolated_network_bridge
    mode      = "none"
    addresses = [var.ip_range]
    dhcp {
        enabled = "false"
    }
    dns {
        enabled = true
    }
    autostart = true
}

#
# Shared disks for sbd if applicable
#
module "sbd_disk" {
    source            = "./modules/shared_disk"
    name              = "sbd"
    storage_pool      = var.storage_pool
    shared_disk_count = var.shared_storage_type == "shared-disk" ? 1 : 0
    shared_disk_size  = var.sbd_disk_size
}
