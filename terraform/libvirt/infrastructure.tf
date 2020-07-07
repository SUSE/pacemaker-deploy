provider "libvirt" {
    uri = var.qemu_uri
}

locals {
    public_network_id    = var.public_bridge == "" && var.public_ip_range != "" ? libvirt_network.public_network.0.id : ""
    private_network_id   = libvirt_network.private_network.0.id
    base_volume_name     = var.source_image != "" ? libvirt_volume.base_image.0.name : var.volume_name != "" ? var.volume_name : ""
}


resource "libvirt_volume" "base_image" {
    count  = var.source_image != "" ? 1 : 0
    name   = "${terraform.workspace}-base-image"
    source = var.source_image
    pool   = var.storage_pool
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
# Shared disks for sbd if applicable
#
module "sbd_disk" {
    source              = "./modules/shared_disk"
    name                = "sbd"
    storage_pool        = var.storage_pool
    shared_disk_enabled = var.shared_storage_type == "shared-disk"
    shared_disk_size    = var.sbd_disk_size
}
