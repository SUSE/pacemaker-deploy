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
    # Load environment from files
    #

    # user provided data
    try:
        with open(filename, "r") as f:
            user_data = json.load(f)
    except Exception as e:
        logging.exception(e)
        return tasks.failure(f"Exception: {e.args}")

    # default values
    with open(f"{utils.path_config()}/defaults.json", "r") as f:
        defaults = json.load(f)

    # merge in environment
    env = utils.merge(defaults, user_data)

    # TODO: check existance of name and provider

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
    logging.info(f"[X] Environment:\n{json.dumps(env, indent = 4)}\n")
    
    #
    # Copy infrastructure files
    #
    logging.info("[X] Copying infrastructure files...")

    # terraform files
    shutil.copytree(utils.path_infrastructure(env["provider"]), path)

    logging.debug(f"Copied tree [{utils.path_infrastructure(env['provider'])}] -> [{path}]")

    # render terraform input variables from environment
    utils.template_render(utils.path_templates(env["provider"]), "terraform.tfvars.j2", path, **env)

    with open(f"{path}/terraform.tfvars", "r") as f:
        logging.debug(f"Rendered terraform.tfvars =\n{f.read()}")

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
        logging.critical(tasks.get_stderr(res))
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

    # switch to workspace
    res = terraform.workspace(path, env["name"])
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

    logging.debug(f"Updated environment =\n{json.dumps(env, indent = 4)}\n")

    logging.info("OK\n")
    
    #
    # Copy provision files
    #
    logging.info("[X] Copying provision files...")

    # render grains files for nodes using enviroment
    for index in range(0, env["terraform"]["node"]["count"]):
        utils.template_render(utils.path_templates(env["provider"]), "node.grains.j2", path, index=index, **env)

        res = tasks.run(f"cd {path} && mv node.grains node-0{index + 1}.grains")
        if tasks.has_failed(res):
            logging.critical(tasks.get_stderr(res))
            return res

        with open(f"{path}/node-0{index + 1}.grains", "r") as f:
            logging.debug(f"Rendered node-0{index + 1}.grains =\n{f.read()}")

    # if there is a iscsi device, render grains file for iscsi using enviroment
    if "public_ip" in env["terraform"]["iscsi"]:
        utils.template_render(utils.path_templates(env["provider"]), "iscsi.grains.j2", path, **env)
        with open(f"{path}/iscsi.grains", "r") as f:
            logging.debug(f"Rendered iscsi.grains =\n{f.read()}")

    # if there is a monitor device, render grains file for monitor using enviroment
    if "public_ip" in env["terraform"]["monitor"]:
        utils.template_render(utils.path_templates(env["provider"]), "monitor.grains.j2", path, **env)
        with open(f"{path}/monitor.grains", "r") as f:
            logging.debug(f"Rendered monitor.grains =\n{f.read()}")
    
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
        logging.critical(tasks.get_stderr(res))
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

    logging.debug(f"Uploads = {uploads}")

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
        logging.debug(f"Uploaded [{origin}] -> [{host}:{destiny}]")
    
    logging.info("OK\n")

    return tasks.success()


def provision_task(host, phases):
    """
    Executes the provisioning in a given host.
    """
    logging.info(f"[{host}] <- Provision launching...")
    
    #
    # Execute provisioning
    #
    for dir, option, phase in phases:
        res = ssh.run("root", "linux", host, f"sh /{dir}/salt/provision.sh -{option} -l /var/log/provision.log")
        if tasks.has_failed(res):
            break

    #
    # Independently of success of provisioning process, cat logs
    #
    destiny = f"./{host}.tmp"
    rcopy = ssh.copy_from_host("root", "linux", host, "/var/log/provision.log", destiny)
    if tasks.has_succeeded(rcopy):
        with open(destiny, "r") as f:
            logging.debug(f"[{host}] provision logs =\n{f.read()}")
    rcopy = ssh.copy_from_host("root", "linux", host, "/var/log/salt/minion", destiny)
    if tasks.has_succeeded(rcopy):
        with open(destiny, "r") as f:
            logging.debug(f"[{host}] provision minion logs =\n{f.read()}")
    tasks.run(f"rm -f {destiny}")

    #
    # Log global result
    #
    if tasks.has_succeeded(res):
        logging.debug(f"[{host}] <- provisioning success")
    else:
        logging.error(f"[{host}] <- provisioning for [{phase}] phase FAILED =\n{tasks.get_stderr(res)}")

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
    
    logging.debug(f"[{subject}] STARTING")

    elapsed = 0
    while(True):
        with clock_task_mutex:
            if clock_task_active == False:
                logging.debug(f"[{subject}] FINISHED in {elapsed} seconds")
                return
        
        time.sleep(1)
        elapsed = elapsed + 1
        if elapsed % 15 == 0:
            logging.debug(f"[{subject}] {elapsed} seconds elapsed")


def provision(name):
    """
    Executes in parallel the provisioning of the nodes.
    """
    #
    # Check deployment does exist
    #
    res, path, env = utils.deployment_verify(name)
    if tasks.has_failed(res):
        logging.critical(tasks.get_stderr(res))
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

    logging.debug(f"Host to provision = {hosts}")

    logging.info("OK\n")
    
    #
    # Launch provision.sh
    #
    logging.info("[X] Launching provisioning...")

    # Prepare tasks
    phases = [("tmp", "i", "install"), ("root", "c", "config"), ("root", "s", "start")]
    global clock_task_mutex
    global clock_task_active
    clock_task_active = True
    clock = threading.Thread(target=clock_task, args=("provision",))
    provision_tasks = [threading.Thread(target=provision_task, args=(host, phases)) for host in hosts]

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
        logging.critical(tasks.get_stderr(res))
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
        logging.critical(tasks.get_stderr(res))
        return res
    else:
        logging.debug(tasks.get_stdout(res))

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
    deploy.py create DEPLOYMENT_FILE [-q] [-f LOG_FILE] [-l LOG_LEVEL]
    deploy.py destroy DEPLOYMENT_NAME [-q] [-f LOG_FILE] [-l LOG_LEVEL]
    deploy.py provision HOST (--only=PROVISION_PHASE | --from=PROVISION_PHASE) [-q] [-f LOG_FILE] [-l LOG_LEVEL]
    deploy.py (-h | --help)
    deploy.py (-v | --version)

Arguments:
    DEPLOYMENT_FILE                      File containing deployment specification
    DEPLOYMENT_NAME                      Name of the deployment (specified on creation inside specification file)
    HOST                                 Host IP to provision

Options:
    -h, --help                           Show this screen.
    -v, --version                        Show version.
    -q, --quiet                          Do not log to stdout
    -f LOG_FILE, --logfile=LOG_FILE      Send logging to file
    -l LOG_LEVEL, --loglevel=LOG_LEVEL   Logging level (one of DEBUG, INFO, WARNING, ERROR, CRITICAL) [default: DEBUG]
    --only=PROVISION_PHASE               Executes only the provision phase specified (one of INSTALL, CONFIG or START)
    --from=PROVISION_PHASE               Executes all provision phases starting from specified

Examples:
    deploy.py create three_node_cluster.json -q --logfile=output.log 
    deploy.py destroy cluster1 --loglevel=WARN
    deploy.py provision --host=10.162.30.40 --from=CONFIG -l CRITICAL
    deploy.py -h
    deploy.py --version

        """
        # log handlers
        handlers = []

        if not arguments["--quiet"]:
            handlers.append(logging.StreamHandler())
        
        if arguments["--logfile"]:
            logfile = arguments["--logfile"]
            handlers.append(logging.FileHandler(logfile,  mode="w"))

        loglevel = utils.get_log_level(arguments["--loglevel"], logging.DEBUG)
        logging.basicConfig(level=loglevel,
                    format="[%(asctime)s] %(levelname)s - %(module)s[%(lineno)d] - %(message)s",
                    datefmt="%m/%d/%Y %I:%M:%S %p",
                    handlers=handlers) 
        
        # if no handlers, full disable logging
        if len(handlers) == 0:
            logging.disable(1024)

        # execute actions
        if arguments["create"]:
            deployment_file = arguments["DEPLOYMENT_FILE"]
            res = create(deployment_file)
            return

        if arguments["destroy"]:
            deployment_name = arguments["DEPLOYMENT_NAME"]
            res = destroy(deployment_name)
            return

        if arguments["provision"]:
            host = arguments["HOST"]
            phase = (arguments["--from"] or arguments["--only"]).upper()
            only = arguments["--only"] != None

            phases = { "INSTALL": ("tmp", "i", "install"), "CONFIG":("root", "c", "config"), "START": ("root", "s", "start") }
            
            if not phase in phases:
                print(f"Used PROVISION_PHASE ({phase}) not in [INSTALL, CONFIG, START]")
                print(f"Use deploy.py --help to show usage")
                return
            
            if only:
                res = provision_task(host, [ phases[phase] ])
            else:
                provision_phases = [ phases[phase] ]
                if phase == "INSTALL":
                    provision_phases.append(phases["CONFIG"])
                    provision_phases.append(phases["START"])
                if phase == "CONFIG":
                    provision_phases.append(phases["START"])

                res = provision_task(host, provision_phases)
            return

    from docopt import docopt
    arguments = docopt(main.__doc__, version='Pacemaker Deploy 0.1.0')
    main(arguments)
