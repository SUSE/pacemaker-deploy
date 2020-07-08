resource "libvirt_volume" "iscsi_image_disk" {
    count            = var.enabled ? 1 : 0
    name             = "${terraform.workspace}-iscsi-disk"    
    pool             = var.storage_pool
    source           = var.source_image
    base_volume_name = var.volume_name
}

resource "libvirt_volume" "iscsi_dev_disk" {
    count = var.enabled ? 1 : 0
    name  = "${terraform.workspace}-iscsi-dev"        
    pool  = var.storage_pool
    size  = var.disk_size
}

resource "libvirt_domain" "iscsi_domain" {
    count      = var.enabled ? 1 : 0
    name       = "${terraform.workspace}-iscsi"        
    vcpu       = var.cpus
    memory     = var.memory
    qemu_agent = true

    dynamic "disk" {
        for_each = [
            {
                "vol_id" = element(libvirt_volume.iscsi_image_disk.*.id, count.index)
            },
            {
                "vol_id" = element(libvirt_volume.iscsi_dev_disk.*.id, count.index)
        }]

        content {
            volume_id = disk.value.vol_id
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
        hostname       = "${terraform.workspace}-iscsi"
        addresses      = [var.iscsi_private_ip]
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
        id         = join("", libvirt_domain.iscsi_domain.*.id)
        hostname   = join("", libvirt_domain.iscsi_domain.*.name)
        private_ip = var.iscsi_private_ip
        public_ip  = join("", libvirt_domain.iscsi_domain.*.network_interface.0.addresses.0)
    }
}
