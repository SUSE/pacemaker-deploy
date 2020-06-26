variable "source_image" {
    description = "Source image used to boot the machines (qcow2 format). It's possible to specify the path to a local (relative to the machine running the terraform command) image or a remote one. Remote images have to be specified using HTTP(S) urls for now."
    type        = string
}

variable "volume_name" {
    description = "Already existing volume name used to boot the machines. It must be in the same storage pool. It's only used if source_image is not provided"
    type        = string
}

variable "storage_pool" {
    description = "Libvirt storage pool name for VM disks"
    type        = string
}

variable "iscsi_enabled" {
    description = "Whether or not to enable this module"
    type        = bool
}

variable "cpus" {
    description = "Number of virtual CPUs"
    type        = number
}

variable "memory" {
    description = "RAM memory in MiB"
    type        = number
}

variable "disk_size" {
    description = "iSCSI partition disk size"
    type        = number
}

variable "iscsi_dev" {
    description = "Device iSCSI for iSCSI server"
    type        = string
}

variable "mac" {
    description = "MAC address in the form AA:BB:CC:11:22:22"
    type        = string
}

variable "bridge" {
    description = "Bridge device name available on the libvirt host, leave default for NAT"
    type        = string
}

variable "nat_network_name" {
    description = "Libvirt NAT network name for VMs, use empty string for bridged networking"
    type        = string
}

variable "isolated_network_id" {
    description = "Network id, internally created by terraform"
    type        = string
}

variable "isolated_network_name" {
    description = "Network name to attach the isolated network interface"
    type        = string
}

variable "iscsi_private_ip" {
    description = "iSCSI server address"
    type        = string
}
