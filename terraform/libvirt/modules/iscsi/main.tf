resource "libvirt_volume" "iscsi_image_disk" {
    count            = var.iscsi_enabled == true ? 1 : 0
    name             = format("%s-iscsi-disk", terraform.workspace)
    source           = var.source_image
    base_volume_name = var.volume_name
    pool             = var.storage_pool
}

resource "libvirt_volume" "iscsi_dev_disk" {
    count = var.iscsi_enabled == true ? 1 : 0
    name  = format("%s-iscsi-dev", terraform.workspace)
    pool  = var.storage_pool
    size  = var.disk_size
}

resource "libvirt_domain" "iscsi_domain" {
    name       = format("%s-iscsi", terraform.workspace)
    memory     = var.memory
    vcpu       = var.cpus
    count      = var.iscsi_enabled == true ? 1 : 0
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
        network_name   = var.nat_network_name
        bridge         = var.bridge
        mac            = var.mac
        wait_for_lease = true
    }

    network_interface {
        network_name = var.isolated_network_name
        network_id   = var.isolated_network_id
        mac          = var.mac
        addresses    = [var.iscsi_private_ip]
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
