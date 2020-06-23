#!/usr/bin/env python3

import os
import shutil
import threading
import logging
import time
import json

import tasks
import terraform
import ssh
import utils

def create(filename):
    """
    Creates a cluster based on the specification file.
    """
    #
    # Load environment from file
    #
    with open(filename, "r") as f:
        env = json.load(f)

    name = env["name"]
    
    #
    # Run phases in sequence
    #
    res = prepare(**env)
    if tasks.has_failed(res):
        logging.critical(f"Phase 'prepare' failed")
        return res
    
    res = infrastructure(name)
    if tasks.has_failed(res):
        logging.critical(f"Phase 'infrastructure' failed")
        return res
    
    res = upload(name)
    if tasks.has_failed(res):
        logging.critical(f"Phase 'upload' failed")
        return res

    res = provision(name)
    if tasks.has_failed(res):
        logging.critical(f"Phase 'provision' failed")
        return res

    return tasks.success()


def prepare(**env):
    """
    Prepare a deployment. Loads initial environment config and stores initial infrastructure files
    """
    #
    # Check deployment does not exist
    #
    name = env["name"]

    if utils.deployment_exists(name):
        res = tasks.failure(f"Deployment {name} already exists")
        logging.critical(tasks.get_stderr(res))
        return res

    path = utils.path_deployment(name)

    #
    # Print environment
    #
    logging.info("[X] Environment:")
    
    logging.info(json.dumps(env, indent = 4))
        
    logging.info("-----------------------------\n")

    #
    # Copy infrastructure files
    #
    logging.info("[X] Copying infrastructure files...")

    # terraform files
    shutil.copytree(utils.path_infrastructure(env["provider"]), path)

    # render terraform input variables from environment
    utils.template_render(utils.path_config(env["provider"]), "terraform.tfvars.j2", path, **env)

    # save the environment
    utils.environment_save(name, **env)
    
    logging.info("OK\n")

    return tasks.success()


def infrastructure(name):
    """
    Create infrastructure for a deployment.
    """
    #
    # Check deployment does exist
    #
    res, path, env = utils.deployment_verify(name)
    if tasks.has_failed(res):
        logging.critical(get_stderr(res))
        return res

    #
    # Create infrastructure
    #
    logging.info("[X] Creating infrastructure...")

    # init
    res = terraform.init(path)
    if tasks.has_failed(res):
        logging.critical(tasks.get_stderr(res))
        return res
    else:
        logging.debug(tasks.get_stdout(res))

    # switch to workspace if present
    if env["terraform"]["workspace"]: 
        res = terraform.workspace(path, env["terraform"]["workspace"])
        if tasks.has_failed(res):
            logging.error(tasks.get_stderr(res))
            return res
        else:
            logging.debug(tasks.get_stdout(res))


    # apply
    res = terraform.apply(path)
    if tasks.has_failed(res):
        logging.critical(tasks.get_stderr(res))
        return res
    else:
        logging.debug(tasks.get_stdout(res))

    logging.info("OK\n")

    #
    # Get terraform outputs
    #
    logging.info("[X] Adding terraform outputs to environment...")

    # capture output
    res = terraform.output(path)
    if tasks.has_failed(res):
        logging.critical(tasks.get_stderr(res))
        return res
    else:
        logging.debug(tasks.get_stdout(res))

    # load as json
    terraform_json = json.loads(tasks.get_stdout(res))

    # translate "a_b = v" outputs to env[terraform][a][b] = v
    for _, (k, v) in enumerate(terraform_json.items()):
        if v["value"]:
            key, _, subkey = k.partition("_")
            env["terraform"][key][subkey] = v["value"]

    # save enriched enviroment data        
    utils.environment_save(name, **env)

    logging.info("OK\n")
    
    #
    # Copy provision files
    #
    logging.info("[X] Copying provision files...")

    # render grains files for nodes using enviroment
    for index in range(0, env["terraform"]["node"]["count"]):
        utils.template_render(utils.path_config(env["provider"]), "node.grains.j2", path, index=index, **env)

        res = tasks.run(f"cd {path} && mv node.grains node-0{index + 1}.grains")
        if tasks.has_failed(res):
            logging.critical(tasks.get_stderr(res))
            return res

    # if there is a iscsi device, render grains file for iscsi using enviroment
    if "public_ip" in env["terraform"]["iscsi"]:
        utils.template_render(utils.path_config(env["provider"]), "iscsi.grains.j2", path, **env)

    # if there is a monitor device, render grains file for monitor using enviroment
    if "public_ip" in env["terraform"]["monitor"]:
        utils.template_render(utils.path_config(env["provider"]), "monitor.grains.j2", path, **env)
    
    logging.info("OK\n")

    return tasks.success()


def upload(name):
    """
    Upload provisioning files for a deployment.
    """
    #
    # Check deployment does exist
    #
    res, path, env = utils.deployment_verify(name)
    if tasks.has_failed(res):
        logging.critical(get_stderr(res))
        return res

    #
    # Calculate uploads
    #
    logging.info("[X] Calculating files to upload...")

    uploads = []
    
    # copy salt directory and grains files to nodes
    for index in range(0, env["terraform"]["node"]["count"]):
        host = env["terraform"]["node"]["public_ips"][index]
        uploads.append( (host, "./salt", "/tmp/salt") )
        uploads.append( (host, f"{path}/node-0{index + 1}.grains", "/tmp/grains") )

    # if there is a iscsi device, copy salt directory and grains file to iscsi device
    if "public_ip" in env["terraform"]["iscsi"]:
        host = env["terraform"]["iscsi"]["public_ip"]
        uploads.append( (host, "./salt", "/tmp/salt") )
        uploads.append( (host, f"{path}/iscsi.grains", "/tmp/grains") )

    # if there is a monitor device, copy salt directory and grains file to monitor device        
    if "public_ip" in env["terraform"]["monitor"]:
        host = env["terraform"]["monitor"]["public_ip"]
        uploads.append( (host, "./salt", "/tmp/salt") )
        uploads.append( (host, f"{path}/monitor.grains", "/tmp/grains") )

    logging.debug(uploads)

    logging.info("OK\n")
    
    #
    # Execute uploads
    #
    logging.info("[X] Uploading files...")
    
    for host, origin, destiny in uploads:
        res = ssh.safe_copy_to_host("root", "linux", host, origin, destiny)
        if tasks.has_failed(res):
            logging.critical(f"Cannot copy [{origin}] -> [{host}:{destiny}]")
            logging.critical(tasks.get_stderr(res))
        logging.info(f"[{origin}] -> [{host}:{destiny}]")
    
    logging.info("OK\n")

    return tasks.success()


def provision_task(host):
    """
    Executes the provisioning in a given host.
    """
    logging.info(f"[{host}] <- Provision launching...")
    
    res = ssh.run("root", "linux", host, "sh /tmp/salt/provision.sh -l /var/log/provision.log")
    if tasks.has_failed(res):
        logging.error(f"[{host}] <- provisioning failed")
        logging.error(tasks.get_stderr(res))
    else:
        logging.info(f"[{host}] <- provisioning success")
        
    return res

#
# Globals to comunicate with clock task
#
clock_task_mutex = threading.Lock()
clock_task_active = True

def clock_task(subject):
    """
    Shows indication of progress for the a given subject, the provisioning in this case, as it may take some time.
    """
    global clock_task_mutex
    global clock_task_active
    
    logging.info(f"[{subject}] Starting at {time.strftime('%X')}")

    elapsed = 0
    while(True):
        with clock_task_mutex:
            if clock_task_active == False:
                logging.info(f"[{subject}] Finished at {time.strftime('%X')}")
                return
        
        time.sleep(1)
        elapsed = elapsed + 1
        if elapsed % 15 == 0:
            logging.info(f"[{subject}] {elapsed} seconds elapsed")


def provision(name):
    """
    Executes in parallel the provisioning of the nodes.
    """
    #
    # Check deployment does exist
    #
    res, path, env = utils.deployment_verify(name)

    if tasks.has_failed(res):
        logging.critical(get_stderr(res))
        return res

    #
    # Calculate hosts
    #
    logging.info("[X] Gathering hosts...")

    hosts = []
    
    # nodes
    for index in range(0, env["terraform"]["node"]["count"]):
        hosts.append(env["terraform"]["node"]["public_ips"][index])

    # iscsi if present
    if "public_ip" in env["terraform"]["iscsi"]:
        hosts.append(env["terraform"]["iscsi"]["public_ip"])

    # monitr if present
    if "public_ip" in env["terraform"]["monitor"]:
        hosts.append(env["terraform"]["monitor"]["public_ip"])

    logging.debug(hosts)

    logging.info("OK\n")
    
    #
    # Launch provision.sh
    #
    logging.info("[X] Launching provisioning...")

    # Prepare tasks
    global clock_task_mutex
    global clock_task_active
    clock_task_active = True
    clock = threading.Thread(target=clock_task, args=("provision",))
    provision_tasks = [threading.Thread(target=provision_task, args=(host,)) for host in hosts]

    # Execute provisioning in parallel
    clock.start() 
    
    for task in provision_tasks:
        task.start()

    for task in provision_tasks:
        task.join()
    
    with clock_task_mutex:        
        clock_task_active = False
    clock.join()
    
    logging.info("OK\n")

    return tasks.success()


def destroy(name):
    """
    Destroys a deployed infrastructure.
    """
    #
    # Check deployment does exist
    #
    res, path, env = utils.deployment_verify(name)
    if tasks.has_failed(res):
        logging.critical(get_stderr(res))
        return res

    #
    # Destroy infrastructure
    #
    logging.info("[X] Destroying infrastructure...")

    if not terraform.is_initialized(path):
        res = tasks.failure(f"Terraform not initiated on {path}")
        logging.critical(tasks.get_stderr(res))
        return res

    res = terraform.destroy(path)
    if tasks.has_failed(res):
        logging.error(f"Cannot destroy Terraform on {path}")
        logging.error(tasks.get_stderr(res))
        return res

    logging.info("OK\n")

    #
    # Deleting deployment
    #
    logging.info("[X] Deleting deployment...")

    shutil.rmtree(path)

    logging.info("OK\n")

    return tasks.success()



if __name__ == "__main__":
    def main(arguments):
        """Pacemaker Deploy.

Usage:
    deploy.py create <deployment_file> [--quiet] [(-l | --logfile) <log_filename>]
    deploy.py destroy <deployment_name> [--quiet] [(-l | --logfile) <log_filename>]
    deploy.py (-h | --help)
    deploy.py --version

Options:
    -h --help     Show this screen.
    --version     Show version.
    --quiet       Do not log to stdout
    -l --logfile  Send logging to file

        """
        # show help or version if asked for
        if arguments["--help"] or arguments["--version"]:
            print(arguments)
            return

        # log handlers
        handlers = []

        if not arguments["--quiet"]:
            handlers.append(logging.StreamHandler())
        
        if arguments["--logfile"]:
            logfile = arguments["<log_filename>"]
            handlers.append(logging.FileHandler(logfile))

        logging.basicConfig(level=logging.DEBUG,
                    format="[%(asctime)s] %(levelname)s - %(message)s",
                    datefmt="%m/%d/%Y %I:%M:%S %p",
                    handlers=handlers) 
        
        # execute actions
        if arguments["create"]:
            deployment_file = arguments["<deployment_file>"]
            res = create(deployment_file)
            return

        if arguments["destroy"]:
            deployment_name = arguments["<deployment_name>"]
            res = destroy(deployment_name)
            return

    from docopt import docopt
    arguments = docopt(main.__doc__, version='Pacemaker Deploy 0.1')
    main(arguments)
