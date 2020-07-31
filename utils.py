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

def path_templates(provider_name):
    """
    Returns template files path for a given provider
    """
    return f"./templates/{provider_name}"


def path_infrastructure(provider_name):
    """
    Returns terraform files path for a given provider
    """
    return f"./terraform/{provider_name}"


def path_deployment_base():
    return "./deployed"


def path_deployment(deployment_name):
    """
    Returns deployment files path for a given deployment
    """
    return f"{path_deployment_base()}/{deployment_name}"


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
        return (tasks.failure(f"Deployment {deployment_name} does not exist"), "", {})

    path = path_deployment(deployment_name)
    
    try:
        env = environment_load(deployment_name)
    except Exception as e:
        return (tasks.failure(f"Inexistant environment file under deployment {deployment_name} = {e.args}"), "", {})
    
    return (tasks.success(), path, env)


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
def template_render(src_dir, template_name, dst_dir, **env):
    input_path = f"{src_dir}/{template_name}"
    
    with open(input_path, "r") as input_file:
        template = jinja2.Template(input_file.read())
    
    template.globals = { "jsonify": json.dumps }
    
    output_name = ".".join( template_name.split(".")[0:-1:] )
    
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


def sink(env):
    new_env = copy.deepcopy(env)

    sinkable_props = ["additional_repos", "additional_pkgs", "cpus", "memory", "disk_size"]

    roles = ["node", "iscsi", "qdevice"]

    for role in roles:
        # images
        if "source_image" not in new_env[role] and "volume_name" not in new_env[role]:
            new_env[role]["source_image"] = new_env["common"]["source_image"]
            new_env[role]["volume_name"] = new_env["common"]["volume_name"]
        if new_env[role]["source_image"]:
            new_env[role]["volume_name"] = ""

        # rest of properties
        for prop in sinkable_props:
            if prop not in new_env[role]:
                new_env[role][prop] = copy.deepcopy(new_env["common"][prop])

    if "disk_size" not in new_env["sbd"]:
        new_env["sbd"]["disk_size"] = copy.deepcopy(new_env["common"]["disk_size"])

    del new_env["common"]["source_image"]
    del new_env["common"]["volume_name"]
    for prop in sinkable_props:
        del new_env["common"][prop]

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

    # nodes
    role = "node"
    for index in range(0, int(env["node"]["count"])):
        name = f"{role}{(index + 1):0>2}"
        host = env[role]["public_ips"][index]
        hosts.append( (role, index, name, host) )

    # if there is a [iscsi, qdevice] device, copy salt directory and grains file
    for role in ["iscsi", "qdevice"]:
        if "public_ip" in env[role]:
            name = role
            host = env[role]["public_ip"]
            hosts.append( (role, 0, name, host) )

    return hosts
