variable "name" {
    description = "Hostname, without the domain part"
    type        = string
}

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

variable "node_count" {
    description = "Number of hosts like this one"
    type        = number
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
    description = "Node partition disk size"
    type        = number
}

variable "public_bridge" {
    description = "Bridge identifier for bridged networking"
    type        = string
}

variable "public_network_id" {
    description = "Network id for NAT public network"
    type        = string
}

variable "private_network_id" {
    description = "Network id, internally created by terraform"
    type        = string
}

variable "node_private_ips" {
    description = "IP addresses to set to the nodes"
    type        = list(string)
}

variable "shared_storage_type" {
    description = "Used shared storage type for fencing (sbd). Available options: iscsi, shared-disk."
    type        = string
}

variable "sbd_disk_id" {
    description = "SBD disk volume id"
    type        = string
}
