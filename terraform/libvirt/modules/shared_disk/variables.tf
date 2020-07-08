variable "enabled" {
    description = "Variable used to decide to create or not the shared disk device"
    type        = bool
}

variable "storage_pool" {
    description = "Libvirt storage pool name for VM disks"
    type        = string
}

variable "disk_size" {
    description = "Shared partition disk size"
    type        = number
}
