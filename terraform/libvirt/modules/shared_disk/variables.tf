variable "name" {
    description = "name of the disk"
    type        = string
}

variable "storage_pool" {
    description = "libvirt storage pool name for VM disks"
    type        = string
}

variable "shared_disk_count" {
    description = "variable used to decide to create or not the shared disk device"
    type        = number
}

variable "shared_disk_size" {
    description = "shared partition disk size"
    type        = number
}
