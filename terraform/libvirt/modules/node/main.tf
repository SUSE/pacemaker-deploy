resource "libvirt_volume" "node_image_disk" {
    count            = var.node_count
    name             = "${terraform.workspace}-${var.name}0${count.index + 1}-main-disk"
    source           = var.source_image
    base_volume_name = var.volume_name
    pool             = var.storage_pool
}

/*
resource "libvirt_volume" "node_data_disk" {
    name  = "${terraform.workspace}-${var.name}0${count.index + 1}-node-disk"
    pool  = var.storage_pool
    count = var.node_count
    size  = var.disk_size
}
*/

resource "libvirt_domain" "node_domain" {
    name       = "${terraform.workspace}-${var.name}0${count.index + 1}"
    memory     = var.memory
    vcpu       = var.cpus
    count      = var.node_count
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
                    // We set null but it will never reached because the slice with 0 cut it off
                    "volume_id" = var.shared_storage_type == "shared-disk" ? var.sbd_disk_id : "null"
                },
            ], 0, var.shared_storage_type == "shared-disk" ? 1 : 0
        )

        content {
            volume_id = disk.value.volume_id
        }
    }

    network_interface {
        wait_for_lease = true
        network_name   = var.nat_network_name
        bridge         = var.bridge
        mac            = var.mac
    }

    network_interface {
        wait_for_lease = false
        network_name   = var.isolated_network_name
        network_id     = var.isolated_network_id
        hostname       = "${terraform.workspace}-${var.name}0${count.index + 1}"
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
