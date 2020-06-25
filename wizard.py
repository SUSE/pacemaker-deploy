#!/usr/bin/env python3
import ipaddress
import json

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


def theme_load(theme_file):
    with open("wizard.theme.json", "r") as f:
        theme_data = f.read()
    return inquirer.themes.load_theme_from_json(theme_data)


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


def validate_shared_storage_type(answers, shared_storage):
    #if shared_storage in ['iscsi']:
    #    raise inquirer.errors.ValidationError('', reason=f'Shared storage {shared_storage} not yet available')
    return True


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


def terraform_generic(theme):
    terraform_generic_questions = [
        inquirer.Text('workspace',
                      message='Enter Terraform workspace'),
    ]
    return inquirer.prompt(terraform_generic_questions, theme=theme)


def libvirt_terraform(theme):

    panel_show("TERRAFORM")
    terraform_answers = terraform_generic(theme)
    print("")


    panel_show("Common questions about the cluster")
    common_questions = [
        inquirer.Text('qemu_uri',
                      message='Enter URI for the KVM hypervisor',
                      default="qemu:///system"),
        inquirer.Text('storage_pool', 
                      message='Enter storage pool',
                      default="default"),
        inquirer.Text('ip_range',
                      message='Enter IP range (cidr format, eg: 192.168.144.0/24)',
                      validate=validate_ip_range),
        inquirer.List('shared_storage_type',
                      message='Select the shared storage type',
                      choices=['shared-disk', 'iscsi'], 
                      validate=validate_shared_storage_type),
        inquirer.Text('sbd_disk_size',
                      message='Enter the size in bytes of the shared storage device disk', 
                      validate=validate_sbd_disk_size, 
                      ignore=lambda answers: answers["shared_storage_type"]=="iscsi"),
    ]
    terraform_answers["common"] = inquirer.prompt(common_questions, theme=theme)
    print("")


    panel_show("Let's talk about the nodes of your cluster")
    node_questions = [
        inquirer.Text('count', 
                      message='Enter the number of nodes',
                      default=3,
                      validate=validate_is_number),
        inquirer.Text('cpus', 
                      message='Enter the number of cpus per node',
                      default=2,
                      validate=validate_is_number),
        inquirer.Text('memory', 
                      message='Enter the nodes memory in MB',
                      default=1024,
                      validate=validate_is_number),
        inquirer.Text('disk_size', 
                      message='Enter the nodes disk size in bytes',
                      default=68719476736,
                      validate=validate_is_number),
    ]
    terraform_answers["node"] = inquirer.prompt(node_questions, theme=theme)
    print("")


    if terraform_answers["common"]["shared_storage_type"] == "iscsi":
        panel_show("iSCSI questions")
        iscsi_questions = [
            inquirer.Text('cpus', 
                          message='Enter the number of cpus for iSCSI node',
                          default=2,
                          validate=validate_is_number),
            inquirer.Text('memory', 
                          message='Enter the iSCSI node memory in MB',
                          default=1024,
                          validate=validate_is_number),
            inquirer.Text('disk_size',
                          message='Enter the iSCSI node disk size in bytes',
                          default=10737418240,
                          validate=validate_is_number),
        ]
        terraform_answers["iscsi"] = inquirer.prompt(iscsi_questions, theme=theme)
        print("")
    else:
        terraform_answers["iscsi"] = {}


    monitor_enabled = inquirer.confirm("Do you want to use a monitor node?", default = False)
    if monitor_enabled:
        panel_show("Monitor questions")
        monitor_questions = [
            inquirer.Text('cpus', 
                          message='Enter the number of cpus for monitor node',
                          default=2,
                          validate=validate_is_number),
            inquirer.Text('memory', 
                          message='Enter the monitor node memory in MB',
                          default=1024,
                          validate=validate_is_number),
        ]
        terraform_answers["monitor"] = inquirer.prompt(monitor_questions, theme=theme)
        terraform_answers["monitor"]["enabled"] = True
        print("")
    else:
        terraform_answers["monitor"] = {}

    return terraform_answers


def salt(terraform_answers, theme):
    salt_answers = {}

    panel_show("PROVISION")
    
    panel_show("Common questions about provisioning")
    common_questions = [
        inquirer.Text('reg_email',
                      message='Enter your registration mail'),
        inquirer.Text('reg_code', 
                      message='Enter your registration code'),
        inquirer.Text('ha_repo',
                      message='Enter HA repository URL',
                      default="http://download.opensuse.org/repositories/network:ha-clustering:sap-deployments:devel"),
    ]
    salt_answers["common"] = inquirer.prompt(common_questions, theme=theme)
    print("")


    panel_show("Node provisioning questions")
    node_questions = [
        inquirer.Text('network_domain', 
                      message='Enter the network domain for nodes',
                      default="tf.local"),
    ]
    salt_answers["node"] = inquirer.prompt(node_questions, theme=theme)
    print("")


    if terraform_answers["common"]["shared_storage_type"] == "iscsi":
        panel_show("iSCSI provisioning questions")
        iscsi_questions = [
            inquirer.Text('network_domain', 
                          message='Enter the network domain for iSCSI node',
                          default="tf.local"),
        ]
        salt_answers["iscsi"] = inquirer.prompt(iscsi_questions, theme=theme)
        print("")
    else:
        salt_answers["iscsi"] = {}


    if "enabled" in terraform_answers["monitor"] and terraform_answers["monitor"]["enabled"]:
        panel_show("Monitor provisioning questions")
        monitor_questions = [
            inquirer.Text('network_domain', 
                          message='Enter the network domain for monitor node',
                          default="tf.local"),
        ]
        salt_answers["monitor"] = inquirer.prompt(monitor_questions, theme=theme)
        print("")
    else:
        salt_answers["monitor"] = {}

    return salt_answers

#
# Main
#
if __name__ == "__main__":
    """
    """
    panel_show("PACEMAKER\n        Deploy", "drpepper")

    theme = theme_load("wizard.theme.json")

    answers = intro(theme)
    answers["terraform"] = libvirt_terraform(theme)
    answers["salt"] = salt(answers["terraform"], theme)
    
    print(f"[X] Environment:\n{json.dumps(answers, indent = 4)}\n")

        #    inquirer.Password('password', message='Please enter your password'),
        #    inquirer.Text('repo', message='Please enter the repo name', default='default'),
        #     inquirer.Text('organization', message='If this is a repo from a organization please enter the organization name, if not just leave this blank'),
        #    inquirer.Confirm('correct',  message='This will delete all your current labels and create a new ones. Continue?', default=False),




"""Colorize text.
    Available text colors:
        red, green, yellow, blue, magenta, cyan, white.
    Available text highlights:
        on_red, on_green, on_yellow, on_blue, on_magenta, on_cyan, on_white.
    Available attributes:
        bold, dark, underline, blink, reverse, concealed.

    http://www.figlet.org/fontdb.cgi

    doom
    shadow
    drpepper
    smshadow
"""
