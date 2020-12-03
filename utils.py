import os
import json
import yaml
import logging
import copy

import jinja2

import tasks


#
# Paths related
#
def path_config():
    """
    Returns global configuration files path
    """
    return f"./config"

def path_infrastructure(provider_name):
    """
    Returns terraform files path for a given provider
    """
    return f"./terraform/{provider_name}"

def path_provision(provider_name):
    """
    Returns salt files path
    """
    return f"./salt"

def path_deployment_base():
    return "./deployed"

def path_deployment(deployment_name):
    """
    Returns deployment files path for a given deployment
    """
    return f"{path_deployment_base()}/{deployment_name}"

def path_deployment_infrastructure(deployment_name):
    return f"{path_deployment(deployment_name)}/terraform"

def path_deployment_provision(deployment_name):
    return f"{path_deployment(deployment_name)}/salt"

#
# Deployment related
#
def deployment_exists(deployment_name):
    """
    Check deployment does exist
    """
    return os.path.exists(path_deployment(deployment_name))


def deployment_verify(deployment_name):
    """
    Check deployment does exist
    """
    if not deployment_exists(deployment_name):
        return (tasks.failure(f"Deployment {deployment_name} does not exist"), {})

    try:
        env = environment_load(deployment_name)
    except Exception as e:
        return (tasks.failure(f"Inexistant environment file under deployment {deployment_name} = {e.args}"), {})
    
    return (tasks.success(), env)


#
# Environment related
#
def environment_name(deployment_name):
    """
    Returns configuration files path for a given provider
    """
    return f"{path_deployment(deployment_name)}/environment.yaml"


def environment_save(deployment_name, **env):
    with open(environment_name(deployment_name), "w") as f:
        yaml.dump(env, f, indent = 4)


def environment_load(deployment_name):
    with open(environment_name(deployment_name), "r") as f:
        env = yaml.load(f, Loader=yaml.FullLoader)
    return env


#
# Jinja templates
#
def template_render(src_dir, template_name, dst_dir, output_name, **env):
    input_path = f"{src_dir}/{template_name}"
    
    with open(input_path, "r") as input_file:
        template = jinja2.Template(input_file.read())

    template.globals = { "jsonify": json.dumps }
    
    #output_name = ".".join( template_name.split(".")[0:-1:] )
    
    output_path = f"{dst_dir}/{output_name}"

    with open(output_path, "w") as output_file:
        output_file.write( template.render(**env) )


#
# Environment file
#
def merge(default, update):
    if not isinstance(default, dict) or not isinstance(update, dict):
        raise TypeError('Parameters are not dictionarys')

    default_copy = default.copy()
    
    for key in update:
        if isinstance(update[key], dict) and isinstance(default.get(key), dict):
            default_copy[key] = merge(default[key], update[key])
        else:
            default_copy[key] = update[key]

    return default_copy


def sink_entry(parent, son, props):
    # images
    if "source_image" in props and "volume_name" in props:
        if "source_image" not in son and "volume_name" not in son:
            son["source_image"] = copy.deepcopy(parent["source_image"])
            son["volume_name"] = copy.deepcopy(parent["volume_name"])
        if "source_image" in son and son["source_image"] != "":
            son["volume_name"] = ""

    # rest of properties
    for prop in props:
        if prop not in ["source_image", "volume_name"] and prop not in son:
            son[prop] = copy.deepcopy(parent[prop])

def delete_from_parent(parent, props):
    for prop in props:
        del parent[prop]

def sinkable_props_for_provider(name):
    if name == "libvirt":
        return ["source_image", "volume_name", "cpus", "memory", "disk_size"]

    if name == "azure":
        return ["vm_size", "offer", "sku", "version", "authorized_keys_file", "public_key_file"]

    return []


def sink(env):
    new_env = copy.deepcopy(env)

    # create all node subkeys
    for index in range(new_env["node"]["count"]):
        value = index + 1
        if value not in new_env["node"]:
            new_env["node"][value] = {}

    # sink all those properties
    sinkable_props = sinkable_props_for_provider(env["provider"]) + ["username", "password", "additional_repos", "additional_pkgs"]

    #if env["provider"] == "libvirt" and "disk_size" not in new_env["sbd"]:
    #    new_env["sbd"]["disk_size"] = copy.deepcopy(new_env["common"]["disk_size"])

    # first from common to the rest of roles
    for role in ["sbd", "node", "iscsi", "qdevice", "examiner"]:
        sink_entry(new_env["common"], new_env[role], sinkable_props)

    delete_from_parent(new_env["common"], sinkable_props)

    # then from node role to specific node id
    for index in range(new_env["node"]["count"]):
        sink_entry(new_env["node"], new_env["node"][index + 1], sinkable_props)

    delete_from_parent(new_env["node"], sinkable_props)

    # erase sbd or iscsi entry
    if new_env["common"]["shared_storage_type"] == "iscsi":
        del new_env["sbd"]
    else:
        del new_env["iscsi"]

    
    if not new_env["qdevice"]["enabled"]:
        del new_env["qdevice"]

    if not new_env["examiner"]["enabled"]:
        del new_env["examiner"]

    return new_env

#
# Others
#
def get_log_level(loglevel, default):

    if loglevel is None:
        return default
        
    loglevels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }

    return loglevels[loglevel.upper()] if loglevel.upper() in loglevels else default


def get_hosts_from_env(env):
    hosts = []

    # if there is a [iscsi, qdevice, examiner] device, copy salt directory and grains file
    # and let them preceed the nodes in the hosts array
    for role in ["iscsi", "qdevice", "examiner"]:
        if role in env and "public_ip" in env[role]:
            name = env[role]["name"]
            host = env[role]["public_ip"]
            username = env[role]["username"]
            password = env[role]["password"]
            hosts.append( (role, 0, name, host, username, password) )

    # nodes
    role = "node"
    for index in range(0, int(env["node"]["count"])):
        name = env[role][index + 1]["name"]
        host = env[role][index + 1]["public_ip"]
        username = env[role][index + 1]["username"]
        password = env[role][index + 1]["password"]
        hosts.append( (role, index + 1, name, host, username, password) )

    return hosts
