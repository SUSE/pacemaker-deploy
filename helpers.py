def provision_keys(name):
    """
    Copies launching node key to all cluster hosts.
    """
    #
    # Check deployment does exist
    #
    res, env = utils.deployment_verify(name)
    if tasks.has_failed(res):
        logging.critical(tasks.get_stderr(res))
        return res

    #
    # Copy keys
    #
    logging.info("[X] Copying ssh key to nodes...")

    hosts = utils.get_hosts_from_env(env)

    commands = []
    for _, _, name, host in hosts:
        command = f'ssh-copy-id -o "StrictHostKeyChecking=no" root@{host}'
        commands.append(command)

    results = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for command in commands:
            futures.append( executor.submit(lambda command: tasks.run(command, input="linux\n"), command) )

        for future in futures:
            results.append( future.result() )

    if functools.reduce(lambda x, y: x or tasks.get_return_code(y) != 0, results, False):
        for result in results:
            if tasks.get_return_code(result) != 0:
                logging.error(tasks.get_stderr(result))
        
        return tasks.failure()

    logging.info("OK\n")

    return tasks.success()


def provision_append_hosts(name):
    """
    Add entries to /etc/hosts
    """
    #
    # Check deployment does exist
    #
    res, env = utils.deployment_verify(name)
    if tasks.has_failed(res):
        logging.critical(tasks.get_stderr(res))
        return res

    #
    # Add hosts
    #
    logging.info("[X] Adding cluster nodes to /etc/hosts...")

    hosts = utils.get_hosts_from_env(env)

    with open('/etc/hosts', 'r') as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        append_line = True
        for _, _, name, host in hosts:
            if host in line or name in line:
                append_line = False
        if append_line:
            new_lines.append(line)

    for _, _, name, host in hosts:
        line = f"{host}  {name}\n"
        new_lines.append(line)

    with open('/etc/hosts', 'w') as f:
        f.writelines(new_lines)

    logging.info("OK\n")

    return tasks.success()


def provision_remove_hosts(name):
    """
    Remove entries from /etc/hosts
    """
    #
    # Check deployment does exist
    #
    res, env = utils.deployment_verify(name)
    if tasks.has_failed(res):
        logging.critical(tasks.get_stderr(res))
        return res

    #
    # Add hosts
    #
    logging.info("[X] Removing cluster nodes to /etc/hosts...")

    hosts = utils.get_hosts_from_env(env)

    with open('/etc/hosts', 'r') as f:
        lines = f.readlines()

    different = False
    new_lines = []
    for line in lines:
        append_line = True
        for _, _, name, host in hosts:
            if host in line or name in line:
                append_line = False
                different = True
        if append_line:
            new_lines.append(line)

    if different:
        with open('/etc/hosts', 'w') as f:
            f.writelines(new_lines)

    logging.info("OK\n")

    return tasks.success()


def provision_add_known_hosts(name):
    """
    Add entries to /etc/hosts
    """
    #
    # Check deployment does exist
    #
    res, env = utils.deployment_verify(name)
    if tasks.has_failed(res):
        logging.critical(tasks.get_stderr(res))
        return res

    #
    # Add hosts
    #
    logging.info("[X] Adding to known_hosts...")

    hosts = utils.get_hosts_from_env(env)

    for _, _, name, _ in hosts:
        command = f"ls"
        res = ssh.run("root", "linux", name, command)

    logging.info("OK\n")

    return tasks.success()


def provision_remove_known_hosts(name):
    """
    Add entries to /etc/hosts
    """
    #
    # Check deployment does exist
    #
    res, env = utils.deployment_verify(name)
    if tasks.has_failed(res):
        logging.critical(tasks.get_stderr(res))
        return res

    #
    # Eliminate entries from known_hosts
    #
    logging.info("[X] Removing servers from known_hosts...")

    hosts = utils.get_hosts_from_env(env)

    try:
        for _, _, host_name, host_ip in hosts:
            tasks.run(f"ssh-keygen -R {host_ip} -f ~/.ssh/known_hosts")
            tasks.run(f"ssh-keygen -R {host_name} -f ~/.ssh/known_hosts")
            logging.info(f"Eliminated from known_hosts [{host_name}={host_ip}]")
    except:
        logging.info("No actions performed...")

    logging.info("OK\n")

    return tasks.success()


