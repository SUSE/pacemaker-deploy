#!/usr/bin/env python3
import ipaddress
import json
import yaml

from pyfiglet import figlet_format
from termcolor import colored
import colorama
import inquirer

import utils


colorama.init()


def panel_show(message, font = ""):
    color = "green"
    high = None
    attrs = ["bold"]
    if font != "":
        message_to_print = figlet_format(message, font=font)
    else:
        message_to_print = message
    print(colored(message_to_print, color, high, attrs))


#
# Validations
#
def validate_is_number(answers, input):
    try:
        n = int(input)
    except ValueError:
        raise inquirer.errors.ValidationError('', reason=f'Invalid format, use numbers')
    return True


def validate_deployment_name(answers, name):
    if name == "":
        raise inquirer.errors.ValidationError('', reason=f'Deployment name must be provided')
    if utils.deployment_exists(name):
        raise inquirer.errors.ValidationError('', reason=f'Deployment {name} already exists')
    return True


def validate_deployment_provider(answers, provider):
    if provider in ['azure', 'aws', 'gcp']:
        raise inquirer.errors.ValidationError('', reason=f'Provider {provider} not yet available')
    return True


def validate_ip_range(answers, ip_range):
    try:
        ipaddress.ip_network(ip_range)
        return True
    except ValueError:
        raise inquirer.errors.ValidationError('', reason=f'Invalid IP cidr range: {ip_range}')


def validate_sbd_disk_size(answers, sbd_disk_size):
    try:
        size = int(sbd_disk_size)
    except ValueError:
        raise inquirer.errors.ValidationError('', reason=f'Invalid format, use numbers')

    if size > 104857600:
        raise inquirer.errors.ValidationError('', reason=f'Disk size bigger than 100MB (too much)')

    if size < 10485760:
        raise inquirer.errors.ValidationError('', reason=f'Disk size smaller than 10MB (too little)')

    return True


#
# Question blocks
#
def intro(theme):
    questions = [
        inquirer.Text('name',
                      message='Enter the new deployment name',
                      validate=validate_deployment_name),
        inquirer.List('provider',
                      message='Select a provider',
                      choices=['libvirt', 'azure', 'aws', 'gcp'],
                      validate=validate_deployment_provider),
    ]
    return inquirer.prompt(questions, theme=theme)


def common_questions(defaults_terraform, defaults_salt):
    return [
        inquirer.Text("qemu_uri",
                      message  = "Enter URI for the KVM hypervisor",
                      default  = defaults_terraform["common"]["qemu_uri"]),
        inquirer.Text("source_image",
                      message  = "Enter the URL for the image used in the machines (alternatively you can enter later a volume name)",
                      default  = defaults_terraform["common"]["source_image"]),
        inquirer.Text("volume_name",
                      message  = "Enter the volume name to be used",
                      default  = defaults_terraform["common"]["volume_name"],
                      ignore   = lambda answers: answers["source_image"]!=""),
        inquirer.Text("storage_pool", 
                      message  = "Enter storage pool",
                      default  = defaults_terraform["common"]["storage_pool"]),
        inquirer.Text("private_ip_range",
                      message  = "Enter IP range (cidr format)",
                      default  = defaults_terraform["common"]["private_ip_range"],
                      validate = validate_ip_range),
        inquirer.Text("public_bridge",
                      message  = "If you have a bridge configured for networking, and want bridged access, set it here (eg: br0)",
                      default  = defaults_terraform["common"]["public_bridge"]),
        inquirer.Text("public_ip_range",
                      message  = "Enter public IP range (cidr format)",
                      default  = defaults_terraform["common"]["public_ip_range"],
                      validate = validate_ip_range,
                      ignore   = lambda answers: answers["public_bridge"]!=""),
        inquirer.List("shared_storage_type",
                      message  = "Select the shared storage type",
                      choices  = ["shared-disk", "iscsi"]),
        inquirer.Text("reg_email",
                      message = "Enter your registration email",
                      default = defaults_salt["common"]["reg_email"]),
        inquirer.Password("reg_code", 
                      message = "Enter your registration code",
                      default = defaults_salt["common"]["reg_code"]),
        inquirer.Text("ha_repo",
                      message  = "What is the HA repository?",
                      default = defaults_salt["common"]["ha_repo"]),
        #inquirer.Text("additional_pkgs",
        #              message = "Packages",
        #              default  = defaults_salt["common"]["additional_pkgs"]),
        #inquirer.Text("additional_repos",
        #              message  = "Repositories", 
        #              default  = defaults_salt["common"]["additional_repos"])
    ]


def node_questions(defaults_terraform, defaults_salt, answers_common):
    return [
        inquirer.Text("source_image",
                      message  = "Do you want to specify a specific source image for cluster nodes? (alternatively leave empty and enter later a volume name)",
                      default  = defaults_terraform["node"]["source_image"] if defaults_terraform["node"]["source_image"] != "" else answers_common["source_image"]),
        inquirer.Text("volume_name",
                      message  = "Enter the volume name to be used in the cluster nodes",
                      default  = defaults_terraform["node"]["volume_name"] if defaults_terraform["node"]["volume_name"] != "" else answers_common["volume_name"],
                      ignore   = lambda answers: answers["source_image"]!=""),
        inquirer.Text("count", 
                      message  = "Enter the number of nodes",
                      default  = defaults_terraform["node"]["count"],
                      validate = validate_is_number),
        inquirer.Text("cpus", 
                      message  = "Enter the number of cpus per node",
                      default  = defaults_terraform["node"]["cpus"],
                      validate = validate_is_number),
        inquirer.Text("memory", 
                      message  = "Enter the nodes memory in MB",
                      default  = defaults_terraform["node"]["memory"],
                      validate = validate_is_number),
        inquirer.Text("disk_size", 
                      message  = "Enter the nodes disk size in bytes",
                      default  = defaults_terraform["node"]["disk_size"],
                      validate = validate_is_number),
        inquirer.Text("network_domain", 
                      message  = "Enter the network domain",
                      default  = defaults_salt["node"]["network_domain"])
    ]


def sbd_questions(defaults_terraform, defaults_salt, answers_common):
    return [
        inquirer.Text("disk_size",
                      message  = "Enter the size in bytes of the shared storage device disk", 
                      validate = validate_sbd_disk_size,
                      default  = defaults_terraform["sbd"]["disk_size"])
    ]


def iscsi_questions(defaults_terraform, defaults_salt, answers_common):
    return [
        inquirer.Text("source_image",
                      message  = "Enter the URL for the image used in the iSCSI machine (alternatively you can enter later a volume name)",
                      default  = defaults_terraform["iscsi"]["source_image"] if defaults_terraform["iscsi"]["source_image"] != "" else answers_common["source_image"]),
        inquirer.Text("volume_name",
                      message  = "Enter the volume name to be used in the iSCSI",
                      default  = defaults_terraform["iscsi"]["volume_name"] if defaults_terraform["iscsi"]["volume_name"] != "" else answers_common["volume_name"],
                      ignore   = lambda answers: answers["source_image"]!=""),
        inquirer.Text("cpus", 
                      message  = "Enter the number of cpus for iSCSI node",
                      default  = defaults_terraform["iscsi"]["cpus"],
                      validate = validate_is_number),
        inquirer.Text("memory", 
                      message  = "Enter the iSCSI node memory in MB",
                      default  = defaults_terraform["iscsi"]["memory"],
                      validate = validate_is_number),
        inquirer.Text("disk_size",
                      message  = "Enter the iSCSI node disk size in bytes",
                      default  = defaults_terraform["iscsi"]["disk_size"],
                      validate = validate_is_number),
        inquirer.Text("network_domain", 
                      message  = "Enter the network domain",
                      default  = defaults_salt["iscsi"]["network_domain"]),
        inquirer.Text("device", 
                      message  = "Enter the iscsi device",
                      default  = defaults_salt["iscsi"]["device"]),
        inquirer.Text("disks",
                      message  = "Enter the iSCSI disks",
                      default  = str(defaults_salt["iscsi"]["disks"]),
                      validate = validate_is_number)
    ]


def monitor_questions(defaults_terraform, defaults_salt, answers_common):
    return [
        inquirer.Confirm("enabled", 
                      message   = "Do you want to use a monitor node?",
                      default   = defaults_terraform["monitor"]["enabled"]),
        inquirer.Text("source_image",
                      message   = "Enter the URL for the image used in the monitor machine (alternatively you can enter later a volume name)",
                      default   = defaults_terraform["monitor"]["source_image"] if defaults_terraform["monitor"]["source_image"] != "" else answers_common["source_image"],
                      ignore    = lambda answers: answers["enabled"] == False),
        inquirer.Text("volume_name",
                      message   = "Enter the volume name to be used in the monitor",
                      default   = defaults_terraform["monitor"]["volume_name"] if defaults_terraform["monitor"]["volume_name"] != "" else answers_common["volume_name"],
                      ignore    = lambda answers: answers["enabled"] == False or answers["source_image"] != ""),
        inquirer.Text("cpus", 
                      message   = "Enter the number of cpus for monitor node",
                      default   = defaults_terraform["monitor"]["cpus"],
                      validate  = validate_is_number,
                      ignore    = lambda answers: answers["enabled"] == False),
        inquirer.Text("memory", 
                      message   = "Enter the monitor node memory in MB",
                      default   = defaults_terraform["monitor"]["memory"],
                      validate  = validate_is_number,
                      ignore    = lambda answers: answers["enabled"] == False),
        inquirer.Text("network_domain", 
                      message   = "Enter the network domain",
                      default   = defaults_salt["monitor"]["network_domain"],
                      ignore    = lambda answers: answers["enabled"] == False)
    ]


def qdevice_questions(defaults_terraform, defaults_salt, answers_common):
    return [
        inquirer.Confirm("enabled", 
                      message   = "Do you want to use a quorum device?",
                      default   = defaults_terraform["qdevice"]["enabled"]),
        inquirer.Text("source_image",
                      message   = "Enter the URL for the image used in the quorum machine (alternatively you can enter later a volume name)",
                      default   = defaults_terraform["qdevice"]["source_image"] if defaults_terraform["qdevice"]["source_image"] != "" else answers_common["source_image"],
                      ignore    = lambda answers: answers["enabled"] == False),
        inquirer.Text("volume_name",
                      message   = "Enter the volume name to be used in the quorum server",
                      default   = defaults_terraform["qdevice"]["volume_name"] if defaults_terraform["qdevice"]["volume_name"] !="" else answers_common["volume_name"],
                      ignore    = lambda answers: answers["enabled"] == False or answers["source_image"] != ""),
        inquirer.Text("network_domain", 
                      message   = "Enter the network domain",
                      default   = defaults_salt["qdevice"]["network_domain"],
                      ignore    = lambda answers: answers["enabled"] == False),
        inquirer.Text("options", 
                      message   = "Are there any more options to use in the quorum server?",
                      default   = defaults_salt["qdevice"]["options"],
                      ignore    = lambda answers: answers["enabled"] == False)
    ]


def libvirt_provider(defaults, theme):
    answers = {}

    panel_show("Common questions about the cluster")
    answers["common"] = inquirer.prompt(common_questions(defaults["terraform"], defaults["salt"]), theme=theme)
    print("")

    panel_show("Let's talk about the nodes of your cluster")
    answers["node"] = inquirer.prompt(node_questions(defaults["terraform"], defaults["salt"], answers["common"]), theme=theme)
    print("")

    if answers["common"]["shared_storage_type"] == "iscsi":
        panel_show("iSCSI questions")
        answers["iscsi"] = inquirer.prompt(iscsi_questions(defaults["terraform"], defaults["salt"], answers["common"]), theme=theme)
        print("")
    else:
        panel_show("SBD questions")
        answers["sbd"] = inquirer.prompt(sbd_questions(defaults["terraform"], defaults["salt"], answers["common"]), theme=theme)
        print("")

    panel_show("Monitor questions")
    answers["monitor"] = inquirer.prompt(monitor_questions(defaults["terraform"], defaults["salt"], answers["common"]), theme=theme)
    print("")

    panel_show("Quorum server questions")
    answers["qdevice"] = inquirer.prompt(qdevice_questions(defaults["terraform"], defaults["salt"], answers["common"]), theme=theme)
    print("")

    return answers



def create_from_answers(answers, defaults):
    deployment = {}

    deployment["name"] = answers["name"]
    deployment["provider"] = answers["provider"]

    deployment["terraform"] = {}
    deployment["salt"] = {}

    ## COMMON
    deployment["terraform"]["common"] = {}
    deployment["terraform"]["common"]["qemu_uri"]            = answers["libvirt"]["common"]["qemu_uri"]
    deployment["terraform"]["common"]["source_image"]        = answers["libvirt"]["common"]["source_image"]
    deployment["terraform"]["common"]["volume_name"]         = answers["libvirt"]["common"]["volume_name"]
    deployment["terraform"]["common"]["storage_pool"]        = answers["libvirt"]["common"]["storage_pool"]
    deployment["terraform"]["common"]["private_ip_range"]    = answers["libvirt"]["common"]["private_ip_range"]
    deployment["terraform"]["common"]["public_bridge"]       = answers["libvirt"]["common"]["public_bridge"]
    deployment["terraform"]["common"]["shared_storage_type"] = answers["libvirt"]["common"]["shared_storage_type"]

    deployment["salt"]["common"] = {}
    deployment["salt"]["common"]["reg_email"]        = answers["libvirt"]["common"]["reg_email"]
    deployment["salt"]["common"]["reg_code"]         = answers["libvirt"]["common"]["reg_code"]
    deployment["salt"]["common"]["ha_repo"]          = answers["libvirt"]["common"]["ha_repo"]
    #deployment["salt"]["common"]["additional_pkgs"]  = answers["libvirt"]["common"]["additional_pkgs"]
    #deployment["salt"]["common"]["additional_repos"] = answers["libvirt"]["common"]["additional_repos"]
    deployment["salt"]["common"]["additional_pkgs"]  = defaults["salt"]["common"]["additional_pkgs"]
    deployment["salt"]["common"]["additional_repos"] = defaults["salt"]["common"]["additional_repos"]

    ## NODE
    deployment["terraform"]["node"] = {}
    deployment["terraform"]["node"]["source_image"] = answers["libvirt"]["node"]["source_image"]
    deployment["terraform"]["node"]["volume_name"]  = answers["libvirt"]["node"]["volume_name"]
    deployment["terraform"]["node"]["count"]        = answers["libvirt"]["node"]["count"]
    deployment["terraform"]["node"]["cpus"]         = answers["libvirt"]["node"]["cpus"]
    deployment["terraform"]["node"]["memory"]       = answers["libvirt"]["node"]["memory"]
    deployment["terraform"]["node"]["disk_size"]    = answers["libvirt"]["node"]["disk_size"]

    deployment["salt"]["node"] = {}
    deployment["salt"]["node"]["network_domain"] = answers["libvirt"]["node"]["network_domain"]

    ## ISCSI / SBD
    deployment["terraform"]["sbd"] = {}
    deployment["terraform"]["iscsi"] = {}
    deployment["salt"]["iscsi"] = {}

    if deployment["terraform"]["common"]["shared_storage_type"] == "shared-disk":
        deployment["terraform"]["sbd"]["disk_size"] = answers["libvirt"]["sbd"]["disk_size"]
        deployment["terraform"]["iscsi"] = defaults["terraform"]["iscsi"]
        deployment["salt"]["iscsi"] = defaults["salt"]["iscsi"]
    else:
        deployment["terraform"]["sbd"] = defaults["terraform"]["sbd"]

        deployment["terraform"]["iscsi"]["source_image"] = answers["libvirt"]["iscsi"]["source_image"]
        deployment["terraform"]["iscsi"]["volume_name"]  = answers["libvirt"]["iscsi"]["volume_name"]
        deployment["terraform"]["iscsi"]["cpus"]         = answers["libvirt"]["iscsi"]["cpus"]
        deployment["terraform"]["iscsi"]["memory"]       = answers["libvirt"]["iscsi"]["memory"]
        deployment["terraform"]["iscsi"]["disk_size"]    = answers["libvirt"]["iscsi"]["disk_size"]

        deployment["salt"]["iscsi"]["network_domain"] = answers["libvirt"]["iscsi"]["network_domain"]
        deployment["salt"]["iscsi"]["device"]         = answers["libvirt"]["iscsi"]["device"]
        deployment["salt"]["iscsi"]["disks"]          = answers["libvirt"]["iscsi"]["disks"]

    ## MONITOR
    deployment["terraform"]["monitor"] = {}
    deployment["salt"]["monitor"] = {}
    
    if answers["libvirt"]["monitor"]["enabled"]:
        deployment["terraform"]["monitor"]["enabled"]      = answers["libvirt"]["monitor"]["enabled"]
        deployment["terraform"]["monitor"]["source_image"] = answers["libvirt"]["monitor"]["source_image"]
        deployment["terraform"]["monitor"]["volume_name"]  = answers["libvirt"]["monitor"]["volume_name"]
        deployment["terraform"]["monitor"]["cpus"]         = answers["libvirt"]["monitor"]["cpus"]
        deployment["terraform"]["monitor"]["memory"]       = answers["libvirt"]["monitor"]["memory"]

        deployment["salt"]["monitor"]["network_domain"] = answers["libvirt"]["monitor"]["network_domain"]
    else:
        deployment["terraform"]["monitor"] = defaults["terraform"]["monitor"]
        deployment["salt"]["monitor"] = defaults["salt"]["monitor"]

    ## QDEVICE
    deployment["terraform"]["qdevice"] = {}
    deployment["salt"]["qdevice"] = {}

    if answers["libvirt"]["qdevice"]["enabled"]:
        deployment["terraform"]["qdevice"]["enabled"]      = answers["libvirt"]["qdevice"]["enabled"]
        deployment["terraform"]["qdevice"]["source_image"] = answers["libvirt"]["qdevice"]["source_image"]
        deployment["terraform"]["qdevice"]["volume_name"]  = answers["libvirt"]["qdevice"]["volume_name"]

        deployment["salt"]["qdevice"]["network_domain"] = answers["libvirt"]["qdevice"]["network_domain"]
        deployment["salt"]["qdevice"]["options"]        = answers["libvirt"]["qdevice"]["options"]
    else:
        deployment["terraform"]["qdevice"] = defaults["terraform"]["qdevice"]
        deployment["salt"]["qdevice"] = defaults["salt"]["qdevice"]

    return deployment

#
# Main
#
if __name__ == "__main__":
    """
    """
    panel_show("PACEMAKER\n        Deploy", "drpepper")

    # theme
    with open(f"{utils.path_config()}/wizard.theme.json", "r") as f:
        theme = inquirer.themes.load_theme_from_json(f.read())

    # default values
    with open(f"{utils.path_config()}/defaults.yaml", "r") as f:
        defaults = yaml.load(f, Loader=yaml.FullLoader)

    answers = intro(theme)
    if answers["provider"] == "libvirt":
        answers["libvirt"] = libvirt_provider(defaults, theme)
    
    deployment = create_from_answers(answers, defaults)

    filename = f"{deployment['name']}.yaml"
    with open(filename, "w") as f:
        yaml.dump(deployment, f, indent = 4)

    print("")
    panel_show(f"All set! Run:")
    panel_show(f"    ./deploy.py create {filename}")


"""
Colorize text:
    Available text colors:
        red, green, yellow, blue, magenta, cyan, white.
    Available text highlights:
        on_red, on_green, on_yellow, on_blue, on_magenta, on_cyan, on_white.
    Available attributes:
        bold, dark, underline, blink, reverse, concealed.

Figlet: http://www.figlet.org/fontdb.cgi
    Nice fonts:
        doom
        shadow
        drpepper
        smshadow
"""
