variable "name" {
    description = "Name of the disk"
    type        = string
}

variable "storage_pool" {
    description = "Libvirt storage pool name for VM disks"
    type        = string
}

variable "shared_disk_enabled" {
    description = "Variable used to decide to create or not the shared disk device"
    type        = bool
}

variable "shared_disk_size" {
    description = "Shared partition disk size"
    type        = number
}
