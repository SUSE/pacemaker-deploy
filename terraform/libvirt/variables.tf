variable "qemu_uri" {
    description = "URI to connect with the qemu service"
    type        = string
}


#
# Common infrastructure
#
variable "source_image" {
    description = "Source image used to boot the machines (qcow2 format). It's possible to specify the path to a local (relative to the machine running the terraform command) image or a remote one. Remote images have to be specified using HTTP(S) urls for now. Specific node images have preference over this value"
    type        = string
}

variable "volume_name" {
    description = "Already existing volume name used to boot the machines. It must be in the same storage pool. It's only used if source_image is not provided. Specific node images have preference over this value"
    type        = string
}

variable "storage_pool" {
    description = "Libvirt storage pool name for VM disks"
    type        = string
}

variable "private_ip_range" {
    description = "IP range of the isolated network"
    type        = string
}

variable "public_ip_range" {
    description = "IP range of the public network (NAT network)"
    type        = string
}

variable "public_bridge" {
    description = "Bridge in the host to allow public access (has precendence over public_ip_range)"
    type        = string
}

#
# Shared disk
#
variable "shared_storage_type" {
    description = "Used shared storage type for fencing (sbd). Available options: iscsi, shared-disk"
    type        = string
}

variable "sbd_disk_size" {
    description = "Disk size (in bytes) for the SBD disk"
    type        = number
}


#
# Cluster Nodes
#
variable "node_source_image" {
    description = "Source image used to boot the node machines (qcow2 format). It's possible to specify the path to a local (relative to the machine running the terraform command) image or a remote one. Remote images have to be specified using HTTP(S) urls for now"
    type        = string
}

variable "node_volume_name" {
    description = "Already existing volume name used to boot the node machines. It must be in the same storage pool. It's only used if source_image is not provided"
    type        = string
}

variable "node_count" {
    description = "Number of nodes"
    type        = number
}

variable "node_cpus" {
    description = "Number of CPUs for the node machines"
    type        = number
}

variable "node_memory" {
    description = "Memory (in MBs) for the node machines"
    type        = number
}

variable "node_disk_size" {
    description = "Disk size (in bytes) for the machines"
    type        = number
}


#
# iSCSI server
#
variable "iscsi_source_image" {
    description = "Source image used to boot the iscsi machines (qcow2 format). It's possible to specify the path to a local (relative to the machine running the terraform command) image or a remote one. Remote images have to be specified using HTTP(S) urls for now"
    type        = string
}

variable "iscsi_volume_name" {
    description = "Already existing volume name used to boot the iscsi machines. It must be in the same storage pool. It's only used if iscsi_source_image is not provided"
    type        = string
}

variable "iscsi_cpus" {
    description = "Number of CPUs for the iSCSI server"
    type        = number
}

variable "iscsi_memory" {
    description = "Memory size (in MBs) for the iSCSI server"
    type        = number
}

variable "iscsi_disk_size" {
    description = "Disk size (in bytes) for the iSCSI server"
    type        = number
}


#
# Monitor
#
variable "monitor_source_image" {
    description = "Source image used to boot the monitor machines (qcow2 format). It's possible to specify the path to a local (relative to the machine running the terraform command) image or a remote one. Remote images have to be specified using HTTP(S) urls for now"
    type        = string
}

variable "monitor_volume_name" {
    description = "Already existing volume name used to boot the monitor machines. It must be in the same storage pool. It's only used if monitoring_source_image is not provided"
    type        = string
}

variable "monitor_enabled" {
    description = "Enable the host to be monitored by exporters, e.g node_exporter"
    type        = bool
}

variable "monitor_cpus" {
    description = "Number of CPUs for the monitor machine"
    type        = number
}

variable "monitor_memory" {
    description = "Memory (in MBs) for the monitor machine"
    type        = number
}
