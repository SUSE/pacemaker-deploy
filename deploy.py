#!/usr/bin/env python3

import os
import shutil
import threading
import concurrent.futures
import functools
import logging
import time
import json
import yaml

import tasks
import terraform
import ssh
import utils


def read_deployment_file(filename):
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
    provider = user_data["provider"]

    with open(f"{utils.path_config()}/defaults.{provider}.yaml", "r") as f:
        defaults = yaml.load(f, Loader=yaml.FullLoader)

    # merge in environment
    env = utils.merge(defaults, user_data)

    # sink group options
    env = utils.sink(env)

    return env


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
    # Create deployment directory
    #
    logging.info("[X] Creating deployment directory...")

    os.mkdir(path)

    # save the environment
    utils.environment_save(name, **env)

    logging.info("OK\n")

    return tasks.success()



def infrastructure_render(name):
    """
    Render infrastructure deployment files
    """

    #
    # Check deployment does exist
    #
    res, env = utils.deployment_verify(name)
    if tasks.has_failed(res):
        logging.critical(tasks.get_stderr(res))
        return res

    #
    # Render infrastructure files
    #
    logging.info("[X] Rendering infrastructure files...")

    path_render = utils.path_deployment_infrastructure(env["name"])
    
    os.mkdir(path_render)

    path_infrastructure = utils.path_infrastructure(env["provider"])

    utils.template_render(path_infrastructure, "main.tf.j2", path_render, "main.tf", **env)
    
    for index in range(0, int(env["node"]["count"])):
        utils.template_render(path_infrastructure, "node.tf.j2", path_render, f"node{(index + 1):0>2}.tf", index = index + 1, **env)

    if(env["provider"] == "libvirt"):
        shutil.copy(path_infrastructure + "/node.xsl", path_render)

    if env["common"]["shared_storage_type"] == "iscsi":
        utils.template_render(path_infrastructure, "iscsi.tf.j2", path_render, "iscsi.tf", **env)

    if env["common"]["shared_storage_type"] == "shared-disk":
        utils.template_render(path_infrastructure, "sbd.tf.j2", path_render, "sbd.tf", **env)
        if(env["provider"] == "libvirt"):
            shutil.copy(path_infrastructure + "/raw.xsl", path_render)

    if "qdevice" in env and env["qdevice"]["enabled"]:
        utils.template_render(path_infrastructure, "qdevice.tf.j2", path_render, "qdevice.tf", **env)
    
    if "examiner" in env and env["examiner"]["enabled"]:
        utils.template_render(path_infrastructure, "examiner.tf.j2", path_render, "examiner.tf", **env)

    logging.info("OK\n")

    return tasks.success()


def infrastructure_execute(name):
    """
    Create infrastructure for a deployment.
    """
    #
    # Check deployment does exist
    #
    res, env = utils.deployment_verify(name)
    if tasks.has_failed(res):
        logging.critical(tasks.get_stderr(res))
        return res

    path_infrastructure = utils.path_deployment_infrastructure(env["name"])

    #
    # Create infrastructure
    #
    logging.info("[X] Creating infrastructure...")

    # init
    logging.info("Initializing Terraform")
    res = terraform.init(path_infrastructure)
    if tasks.has_failed(res):
        logging.critical(tasks.get_stderr(res))
        return res
    else:
        logging.debug(tasks.get_stdout(res))

    # apply
    logging.info(f"Executing plan")
    res = terraform.apply(path_infrastructure)
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

    # refresh
    logging.info(f"Refreshing output")
    res = terraform.refresh(path_infrastructure)
    if tasks.has_failed(res):
        logging.critical(tasks.get_stderr(res))
        return res
    else:
        logging.debug(tasks.get_stdout(res))

    # capture output
    logging.info(f"Capturing output")
    res = terraform.output(path_infrastructure)
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
            if "node" in key:
                key, _, index = key.partition("0")
                env[key][int(index)][subkey] = v["value"]
            else:
                env[key][subkey] = v["value"]

    # save enriched enviroment data        
    utils.environment_save(name, **env)
    
    logging.info(f"Updated environment")
    logging.debug(f"{json.dumps(env, indent = 4)}\n")

    logging.info("OK\n")
    
    return tasks.success()


def provision_render(name):
    """
    Render salt files for a deployment.
    """
    #
    # Check deployment does exist
    #
    res, env = utils.deployment_verify(name)
    if tasks.has_failed(res):
        logging.critical(tasks.get_stderr(res))
        return res

    #
    # Copy provision files
    #
    logging.info("[X] Rendering provision files...")

    path_render = utils.path_deployment_provision(env["name"])
    
    try:
        os.mkdir(path_render)
    except:
        pass

    path_provision = utils.path_provision(env["provider"])

    for role, index, name, _, _, _ in utils.get_hosts_from_env(env):
        utils.template_render(path_provision, "grains.j2", path_render, f"{name}.grains", role=role, index=index, env=env, **env)

        logging.info(f"Rendered {name}.grains")
        with open(f"{path_render}/{name}.grains", "r") as f:
            logging.debug(f"{f.read()}")

    logging.info("OK\n")

    return tasks.success()


def upload_task(name, host, username, password, origin, destiny):
    res = ssh.safe_copy_to_host(username, password, host, origin, destiny)
    if tasks.has_failed(res):
        logging.critical(f"Cannot copy [{origin}] -> [({name}={host}):{destiny}]")
        logging.critical(tasks.get_stderr(res))
    
    logging.info(f"Uploaded [{origin}] -> [({name}={host}):{destiny}]")


def upload(name):
    """
    Upload provisioning files for a deployment.
    """
    #
    # Check deployment does exist
    #
    res, env = utils.deployment_verify(name)
    if tasks.has_failed(res):
        logging.critical(tasks.get_stderr(res))
        return res

    #
    # Execute uploads
    #
    logging.info("[X] Uploading files...")

    for role, _, name, host, username, password in utils.get_hosts_from_env(env):
        command = f"mkdir /tmp/salt"
        res = ssh.run(username, password, host, command)
        if tasks.has_failed(res):
            logging.info(f"Cannot create directory structure on [{name}={host}]")
            logging.info(tasks.get_stderr(res))
            return res

        command = f"mkdir /tmp/salt/file_roots"
        res = ssh.run(username, password, host, command)
        if tasks.has_failed(res):
            logging.info(f"Cannot create directory structure on [{name}={host}]")
            logging.info(tasks.get_stderr(res))
            return res

    uploads = []

    # copy salt directory and grains files to machines
    path_deployment_provision = utils.path_deployment_provision(env["name"])
    path_provision = utils.path_provision(env["name"])
    for role, _, name, host, username, password in utils.get_hosts_from_env(env):
        uploads.append( (name, host, username, password, f"{path_provision}/provision.sh", f"/tmp/salt/") )
        uploads.append( (name, host, username, password, f"{path_provision}/minion", "/tmp/salt/") )
        uploads.append( (name, host, username, password, f"{path_deployment_provision}/{name}.grains", "/tmp/salt/grains") )
        uploads.append( (name, host, username, password, f"{path_provision}/{role}/file_roots", f"/tmp/salt/") )
        uploads.append( (name, host, username, password, f"{path_provision}/common", "/tmp/salt/file_roots/") )
        uploads.append( (name, host, username, password, f"{path_provision}/{role}/pillar_roots", f"/tmp/salt/file_roots") )
        

    upload_tasks  = [threading.Thread(target=upload_task, args=(name, host, username, password, origin, destiny)) for name, host, username, password, origin, destiny in uploads]

    # Execute upload in parallel
    for task in upload_tasks:
        task.start()

    for task in upload_tasks:
        task.join()

    logging.info("OK\n")

    return tasks.success()


def provision_task(name, host, username, password, phases):
    """
    Executes the provisioning in a given host.
    """
    #
    # Execute provisioning
    #
    for phase in phases:
        res = ssh.run(username, password, host, f"sudo sh /tmp/salt/provision.sh -{phase[0]} -l /var/log/provision.log")
        if tasks.has_failed(res):
            logging.info(f"phase {phase} error -> [{name}={host}]")
            break
        else:
            logging.info(f"phase {phase} executed -> [{name}={host}]")

    #
    # Independently of success of provisioning process, cat logs
    #
    destiny = f"./{name}.tmp"
    #logs = ["/var/log/provision.log", "/var/log/salt/minion"]
    logs = ["/var/log/provision.log"]
    for log in logs:
        rcopy = ssh.copy_from_host(username, password, host, log, destiny)
        if tasks.has_succeeded(rcopy):
            with open(destiny, "r") as f:
                logging.debug(f"[{name}={host}] {log} =\n{f.read()}")
    tasks.run(f"rm -f {destiny}")

    #
    # Log global result
    #
    if tasks.has_succeeded(res):
        logging.info(f"provisioning SUCCESS -> [{name}={host}] for {phases}")
    else:
        logging.error(f"provisioning FAILED -> [{name}={host}] for {phases}")

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


def provision_execute(name):
    """
    Executes in parallel the provisioning of the nodes.
    """
    #
    # Check deployment does exist
    #
    res, env = utils.deployment_verify(name)
    if tasks.has_failed(res):
        logging.critical(tasks.get_stderr(res))
        return res

    #
    # Launch provision.sh
    #
    global clock_task_mutex
    global clock_task_active

    logging.info("[X] Launching provisioning...")

    hosts = utils.get_hosts_from_env(env)

    # Prepare tasks
    #phases = ["install", "config", "start"]
    clock_task_active = True
    clock = threading.Thread(target=clock_task, args=("clock",))

    # Execute provisioning in mostly parallel (first a group of machines, then the second one)
    logging.info(f"Provisioning nodes")
   
    clock.start()     

    group1 = [ host for host in hosts]
    group2 = [ host for host in hosts]
    group3 = [ host for host in hosts if host[0] != "node" or "node01" in host[2]]
    group4 = [ host for host in hosts if host[0] == "node" and "node01" not in host[2]]

    provision_tasks1  = [(provision_task, name, host, username, password, ["install", "config"]) for role, index, name, host, username, password in group1]
    provision_tasks2  = [(provision_task, name, host, username, password, ["rendezvous"])        for role, index, name, host, username, password in group2]    
    provision_tasks3  = [(provision_task, name, host, username, password, ["start"])             for role, index, name, host, username, password in group3]
    stages = [provision_tasks1, provision_tasks2, provision_tasks3]

    serialized_joining = False
    if serialized_joining: #"qdevice" in env and env["qdevice"]["enabled"]:
        for _, _, name, host, username, password in group4:
            provision_tasks = [(provision_task, name, host, username, password, ["start"])]
            stages.append(provision_tasks)
    else:
        provision_tasks = [(provision_task, name, host, username, password, ["start"]) for role, index, name, host, username, password in group4]
        stages.append(provision_tasks)


    for stage in stages:
        logging.info(f"Running stage")
        results = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for task in stage:
                function, host_name, host_ip, username, password, parameters = task
                futures.append( executor.submit(function, host_name, host_ip, username, password, parameters) )
    
            for future in futures:
                results.append( future.result() )

        if functools.reduce(lambda x, y: x or tasks.get_return_code(y) != 0, results, False):
            break
    
    with clock_task_mutex:        
        clock_task_active = False
    clock.join()

    logging.info("OK\n")

    return tasks.success()


def create_infrastructure(filename):
    
    env = read_deployment_file(filename)

    # TODO: check existance of name and provider

    name = env["name"]
    
    #
    # Run phases in sequence
    #
    res = prepare(**env)
    if tasks.has_failed(res):
        logging.critical(f"Phase 'prepare' failed")
        return res
    
    res = infrastructure_render(name)
    if tasks.has_failed(res):
        logging.critical(f"Phase 'infrastructure_render' failed")
        return res

    res = infrastructure_execute(name)
    if tasks.has_failed(res):
        logging.critical(f"Phase 'infrastructure_execute' failed")
        return res

    return tasks.success()


def create_provision(filename):
    
    env = read_deployment_file(filename)

    # TODO: check existance of name and provider

    name = env["name"]
    
    res = provision_render(name)
    if tasks.has_failed(res):
        logging.critical(f"Phase 'provision_render' failed")
        return res

    res = upload(name)
    if tasks.has_failed(res):
        logging.critical(f"Phase 'upload' failed")
        return res

    res = provision_execute(name)
    if tasks.has_failed(res):
        logging.critical(f"Phase 'provision_execute' failed")
        return res

    return tasks.success()


def create_all(filename):

    res = create_infrastructure(filename)
    if tasks.has_failed(res):
        return res

    res = create_provision(filename)
    if tasks.has_failed(res):
        return res

    return res


def destroy_task(name, host, username, password):
    """
    Destroys the provisioning in a given host.
    """
    res = ssh.run(username, password, host, f"sudo sh /tmp/salt/provision.sh -d -l /var/log/destroying.log")
        
    logging.info(f"Provision destroy on [{name}={host}]")
 
    return res


def destroy(filename):
    """
    Destroys a deployed infrastructure.
    """
    env = read_deployment_file(filename)
    name = env["name"]

    #
    # Check deployment does exist
    #
    res, env = utils.deployment_verify(name)
    if tasks.has_failed(res):
        logging.critical(tasks.get_stderr(res))
        return res

    path = utils.path_deployment(env["name"])

    #
    # Execute on destroy actions on nodes
    #
    logging.info("[X] Executing on destroy actions on nodes...")

    try:
        hosts = utils.get_hosts_from_env(env)

        destroy_tasks  = [threading.Thread(target=destroy_task, args=(name, host, username, password)) for role, index, name, host, username, password in hosts]

        for task in destroy_tasks:
            task.start()

        for task in destroy_tasks:
            task.join()

    except:
        logging.info("No actions performed...")

    logging.info("OK\n")

    #
    # Eliminate entries from known_hosts
    #
    logging.info("[X] Removing servers from known_hosts...")

    try:
        hosts = utils.get_hosts_from_env(env)
        
        for _, _, host_name, host_ip, _, _ in hosts:
            tasks.run(f"ssh-keygen -R {host_ip} -f ~/.ssh/known_hosts")
            logging.info(f"Eliminated from known_hosts [{host_name}={host_ip}]")
    except:
        logging.info("No actions performed...")

    logging.info("OK\n")


    #
    # Destroy infrastructure
    #
    logging.info("[X] Destroying infrastructure...")

    path_infrastructure = utils.path_deployment_infrastructure(env["name"])

    if not terraform.is_initialized(path_infrastructure):
        res = tasks.failure(f"Terraform not initiated on {path}")
        logging.critical(tasks.get_stderr(res))
        return res

    res = terraform.destroy(path_infrastructure)
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
    deploy.py infrastructure DEPLOYMENT_FILE [-q] [-f LOG_FILE] [-l LOG_LEVEL]
    deploy.py provision DEPLOYMENT_FILE [-q] [-f LOG_FILE] [-l LOG_LEVEL]
    deploy.py destroy DEPLOYMENT_FILE [-q] [-f LOG_FILE] [-l LOG_LEVEL]
    deploy.py (-h | --help)
    deploy.py (-v | --version)

Arguments:
    DEPLOYMENT_FILE                      File containing deployment specification
    HOST                                 Host IP to provision

Options:
    -h, --help                           Show this screen.
    -v, --version                        Show version.
    -q, --quiet                          Do not log to stdout
    -f LOG_FILE, --logfile=LOG_FILE      Send logging to file
    -l LOG_LEVEL, --loglevel=LOG_LEVEL   Logging level (one of DEBUG, INFO, WARNING, ERROR, CRITICAL) [default: INFO]

Examples:
    deploy.py create three_node_cluster.json -q --logfile=output.log 
    deploy.py destroy cluster1 --loglevel=WARN
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
            res = create_all(deployment_file)
            return res

        if arguments["infrastructure"]:
            deployment_file = arguments["DEPLOYMENT_FILE"]
            res = create_infrastructure(deployment_file)
            return res

        if arguments["provision"]:
            deployment_file = arguments["DEPLOYMENT_FILE"]
            res = create_provision(deployment_file)
            return res

        if arguments["destroy"]:
            deployment_file = arguments["DEPLOYMENT_FILE"]
            res = destroy(deployment_file)
            return res

    from docopt import docopt
    arguments = docopt(main.__doc__, version='Pacemaker Deploy 0.1.0')
    main(arguments)
