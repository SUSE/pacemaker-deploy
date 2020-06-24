import os
import json
import logging

import jinja2

import tasks


#
# Paths related
#
def path_config(provider_name):
    """
    Returns configuration files path for a given provider
    """
    return f"./config/{provider_name}"


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
        return (tasks.failure(f"Inexistant environment file under deployment {deployment_name}"), "", {})
    
    return (tasks.success(), path, env)


#
# Environment related
#
def environment_name(deployment_name):
    """
    Returns configuration files path for a given provider
    """
    return f"{path_deployment(deployment_name)}/environment.json"


def environment_save(deployment_name, **env):
    with open(environment_name(deployment_name), "w+") as f:
        json.dump(env, f, indent = 4)


def environment_load(deployment_name):
    with open(environment_name(deployment_name), "r") as f:
        env = json.load(f)
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

    with open(output_path, "w+") as output_file:
        output_file.write( template.render(**env) )


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
