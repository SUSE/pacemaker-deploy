resource "libvirt_volume" "node_image_disk" {
    count            = var.node_count
    name             = "${terraform.workspace}-node0${count.index + 1}-main-disk"
    pool             = var.storage_pool
    source           = var.source_image
    base_volume_name = var.volume_name
}

/*
resource "libvirt_volume" "node_data_disk" {
    count = var.node_count
    name  = "${terraform.workspace}-node0${count.index + 1}-node-disk"
    pool  = var.storage_pool
    size  = var.disk_size
}
*/

resource "libvirt_domain" "node_domain" {
    count      = var.node_count
    name       = "${terraform.workspace}-node0${count.index + 1}"
    vcpu       = var.cpus
    memory     = var.memory
    qemu_agent = true

    dynamic "disk" {
        for_each = [
            {
                "vol_id" = element(libvirt_volume.node_image_disk.*.id, count.index)
            }
        ]

        content {
            volume_id = disk.value.vol_id
        }
    }
    
    /*
    dynamic "disk" {
        for_each = [
            {
                "vol_id" = element(libvirt_volume.node_image_disk.*.id, count.index)
            },
            {
                "vol_id" = element(libvirt_volume.node_data_disk.*.id, count.index)
            },
        ]

        content {
            volume_id = disk.value.vol_id
        }
    }
    */

    dynamic "disk" {
        for_each = slice(
            [
                {
                    "volume_id" = var.sbd_disk_id
                },
            ], 0, var.sbd_disk_id != "" ? 1 : 0
        )

        content {
            volume_id = disk.value.volume_id
        }
    }

    network_interface {
        wait_for_lease = true
        network_id     = var.public_network_id
        bridge         = var.public_bridge
    }

    network_interface {
        wait_for_lease = false
        network_id     = var.private_network_id
        hostname       = "${terraform.workspace}-name0${count.index + 1}"
        addresses      = [element(var.node_private_ips, count.index)]
    }

    xml {
        xslt = file("modules/node/shareable.xsl")
    }

    console {
        type        = "pty"
        target_port = "0"
        target_type = "serial"
    }

    console {
        type        = "pty"
        target_type = "virtio"
        target_port = "1"
    }

    graphics {
        type        = "spice"
        listen_type = "address"
        autoport    = true
    }

    cpu = {
        mode = "host-passthrough"
    }
}

output "output_data" {
    value = {
        ids         = libvirt_domain.node_domain.*.id
        hostnames   = libvirt_domain.node_domain.*.name
        private_ips = var.node_private_ips
        public_ips  = libvirt_domain.node_domain.*.network_interface.0.addresses.0
    }
}
