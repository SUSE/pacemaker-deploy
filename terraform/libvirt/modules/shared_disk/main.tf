resource "libvirt_volume" "shared_disk" {
    count = var.enabled ? 1 : 0
    name  = "${terraform.workspace}-sbd.raw"
    pool  = var.storage_pool
    size  = var.disk_size

    xml {
        xslt = file("modules/shared_disk/raw.xsl")
    }
}

output "id" {
    value = join(",", libvirt_volume.shared_disk.*.id)
}
