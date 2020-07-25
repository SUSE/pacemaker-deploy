#!/usr/bin/env python3

import os
import shutil
import threading
import logging
import time
import json
import yaml

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
            user_data = yaml.load(f, Loader=yaml.FullLoader)
    except Exception as e:
        logging.exception(e)
        return tasks.failure(f"Exception: {e.args}")

    # default values
    with open(f"{utils.path_config()}/defaults.yaml", "r") as f:
        defaults = yaml.load(f, Loader=yaml.FullLoader)

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

    logging.info(f"Copied tree [{utils.path_infrastructure(env['provider'])}] -> [{path}]")

    # render terraform input variables from environment
    utils.template_render(utils.path_templates(env["provider"]), "terraform.tfvars.j2", path, **env)

    logging.info("Rendered terraform.tfvars")
    with open(f"{path}/terraform.tfvars", "r") as f:
        logging.debug(f"{f.read()}")

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
    logging.info("Initializing Terraform")
    res = terraform.init(path)
    if tasks.has_failed(res):
        logging.critical(tasks.get_stderr(res))
        return res
    else:
        logging.debug(tasks.get_stdout(res))

    # switch to workspace
    logging.info(f"Switching to workspace {env['name']}")
    res = terraform.workspace(path, env["name"])
    if tasks.has_failed(res):
        logging.error(tasks.get_stderr(res))
        return res
    else:
        logging.debug(tasks.get_stdout(res))

    # apply
    logging.info(f"Executing plan")
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
    logging.info(f"Capturing output")
    res = terraform.output(path)
    if tasks.has_failed(res):
        logging.critical(tasks.get_stderr(res))
        return res
    else:
        logging.debug(tasks.get_stdout(res))

    # load as json
    terraform_json = json.loads(tasks.get_stdout(res))

    # translate "a_b = v" outputs to env[terraform][a][b] = v
    logging.info(f"Translating output")
    for _, (k, v) in enumerate(terraform_json.items()):
        if v["value"]:
            key, _, subkey = k.partition("_")
            env["terraform"][key][subkey] = v["value"]

    # save enriched enviroment data        
    utils.environment_save(name, **env)
    
    logging.info(f"Updated environment")
    logging.debug(f"{json.dumps(env, indent = 4)}\n")

    logging.info("OK\n")
    
    #
    # Copy provision files
    #
    logging.info("[X] Copying provision files...")

    # render grains files for nodes using enviroment
    for index in range(0, int(env["terraform"]["node"]["count"])):
        utils.template_render(utils.path_templates(env["provider"]), "node.grains.j2", path, index=index, **env)

        res = tasks.run(f"cd {path} && mv node.grains node-0{index + 1}.grains")
        if tasks.has_failed(res):
            logging.critical(tasks.get_stderr(res))
            return res

        logging.info(f"Rendered node-0{index + 1}.grains")
        with open(f"{path}/node-0{index + 1}.grains", "r") as f:
            logging.debug(f"{f.read()}")

    # if there is a iscsi device, render grains file for iscsi using enviroment
    if "public_ip" in env["terraform"]["iscsi"]:
        utils.template_render(utils.path_templates(env["provider"]), "iscsi.grains.j2", path, **env)

        logging.info("Rendered iscsi.grains")
        with open(f"{path}/iscsi.grains", "r") as f:
            logging.debug(f"{f.read()}")

    # if there is a monitor device, render grains file for monitor using enviroment
    if "public_ip" in env["terraform"]["monitor"]:
        utils.template_render(utils.path_templates(env["provider"]), "monitor.grains.j2", path, **env)

        logging.info("Rendered monitor.grains")
        with open(f"{path}/monitor.grains", "r") as f:
            logging.debug(f"{f.read()}")

    # if there is a qdevice, render grains file for qdevice using enviroment
    if "public_ip" in env["terraform"]["qdevice"]:
        utils.template_render(utils.path_templates(env["provider"]), "qdevice.grains.j2", path, **env)

        logging.info("Rendered qdevice.grains")
        with open(f"{path}/qdevice.grains", "r") as f:
            logging.debug(f"{f.read()}")

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
    for index in range(0, int(env["terraform"]["node"]["count"])):
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

    # if there is a qdevice, copy salt directory and grains file to qdevice device
    if "public_ip" in env["terraform"]["qdevice"]:
        host = env["terraform"]["qdevice"]["public_ip"]
        uploads.append( (host, "./salt", "/tmp/salt") )
        uploads.append( (host, f"{path}/qdevice.grains", "/tmp/grains") )

    logging.info(f"{uploads}")

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
    
        logging.info(f"Uploaded [{origin}] -> [{host}:{destiny}]")
    
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
    for phase in phases:
        res = ssh.run("root", "linux", host, f"sh /tmp/salt/provision.sh -{phase[0]} -l /var/log/provision.log")
        if tasks.has_failed(res):
            logging.info(f"[{host}] <- phase {phase} failed")
            break
        else:
            logging.info(f"[{host}] <- phase {phase} executed")

    #
    # Independently of success of provisioning process, cat logs
    #
    destiny = f"./{host}.tmp"
    #logs = ["/var/log/provision.log", "/var/log/salt/minion"]
    logs = ["/var/log/provision.log"]
    for log in logs:
        rcopy = ssh.copy_from_host("root", "linux", host, log, destiny)
        if tasks.has_succeeded(rcopy):
            with open(destiny, "r") as f:
                logging.debug(f"[{host}] {log} =\n{f.read()}")
    tasks.run(f"rm -f {destiny}")

    #
    # Log global result
    #
    if tasks.has_succeeded(res):
        logging.info(f"[{host}] <- provisioning success")
    else:
        logging.error(f"[{host}] <- provisioning FAILED, continue provisioning with => deploy.py provision {host} --from={phase}")

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
    
    logging.info(f"[{subject}] STARTING")

    elapsed = 0
    while(True):
        with clock_task_mutex:
            if clock_task_active == False:
                logging.info(f"[{subject}] FINISHED in {elapsed} seconds")
                return
        
        time.sleep(1)
        elapsed = elapsed + 1
        if elapsed % 30 == 0:
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
        logging.critical(tasks.get_stderr(res))
        return res

    #
    # Calculate hosts
    #
    logging.info("[X] Gathering hosts...")

    hosts_first  = utils.get_hosts_from_env_first(env)
    hosts_second = utils.get_hosts_from_env_second(env)

    logging.info(f"Host to provision first  = {hosts_first}")
    logging.info(f"Host to provision second = {hosts_second}")

    logging.info("OK\n")
    
    #
    # Launch provision.sh
    #
    logging.info("[X] Launching provisioning...")

    # Prepare tasks
    phases = ["install", "config", "start"]
    global clock_task_mutex
    global clock_task_active
    clock_task_active = True
    clock = threading.Thread(target=clock_task, args=("provision",))
    provision_join_tasks_first  = [threading.Thread(target=provision_task, args=(host, phases)) for host in hosts_first]
    provision_join_tasks_second = [threading.Thread(target=provision_task, args=(host, phases)) for host in hosts_second]

    # Execute provisioning in mostly parallel (first a group of machines, then the second one)
    clock.start() 

    logging.info(f"Provisioning nodes (first group)")

    for task in provision_join_tasks_first:
        task.start()

    for task in provision_join_tasks_first:
        task.join()

    logging.info(f"Provisioning nodes (second group)")

    for task in provision_join_tasks_second:
        task.start()

    for task in provision_join_tasks_second:
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
    # Execute on destroy actions on nodes
    #
    logging.info("[X] Executing on destroy actions on nodes...")

    hosts = utils.get_hosts_from_env(env)

    for host in hosts:
        ssh.run("root", "linux", host, f"sh /tmp/salt/provision.sh -d -l /var/log/destroying.log")

    logging.info("OK\n")

    #
    # Eliminate entries from known_hosts
    #
    logging.info("[X] Eliminating server from known_hosts...")

    hosts = utils.get_hosts_from_env(env)

    for host in hosts:
        tasks.run(f"ssh-keygen -R {host} -f ~/.ssh/known_hosts")

    logging.info("OK\n")

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
    -l LOG_LEVEL, --loglevel=LOG_LEVEL   Logging level (one of DEBUG, INFO, WARNING, ERROR, CRITICAL) [default: INFO]
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

        loglevel = utils.get_log_level(arguments["--loglevel"], logging.INFO)
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

            if not phase in ["INSTALL", "CONFIG", "START"]:
                print(f"Used PROVISION_PHASE ({phase}) not in [INSTALL, CONFIG, START]")
                print(f"Use deploy.py --help to show usage")
                return
            
            if only:
                res = provision_task(host, [ phase.lower() ] )
            else:
                provision_phases = [ phase.lower() ]
                if phase == "INSTALL":
                    provision_phases.append("config")
                    provision_phases.append("start")
                if phase == "CONFIG":
                    provision_phases.append("start")

                res = provision_task(host, provision_phases)
            return

    from docopt import docopt
    arguments = docopt(main.__doc__, version='Pacemaker Deploy 0.1.0')
    main(arguments)
