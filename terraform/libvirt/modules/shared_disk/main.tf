resource "libvirt_volume" "shared_disk" {
    name  = "${terraform.workspace}-${var.name}.raw"
    pool  = var.storage_pool
    size  = var.shared_disk_size
    count = var.shared_disk_enabled ? 1 : 0

    xml {
        xslt = file("modules/shared_disk/raw.xsl")
    }
}

output "id" {
    value = join(",", libvirt_volume.shared_disk.*.id)
}
