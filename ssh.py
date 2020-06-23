import time

import tasks


def run(user, password, host, command):
    """
    Execute a command in a remote host
    """
    remote_command = f"sshpass -p {password} ssh -o StrictHostKeyChecking=no {user}@{host} {command}"
    return tasks.run(remote_command)


def copy_to_host(user, password, host, origin, destination):
    """
    Copy a local directory to a remote host
    """
    command = f"sshpass -p {password} scp -o StrictHostKeyChecking=no -r {origin} {user}@{host}:{destination}"
    return tasks.run(command)


def copy_from_host(user, password, host, origin, destination):
    """
    Copy a local directory to a remote host
    """
    command = f"sshpass -p {password} scp -o StrictHostKeyChecking=no -r {user}@{host}:{origin} {destination}"
    return tasks.run(command)


def safe_copy_to_host(user, password, host, origin, destination):
    """
    Copy a local directory to a remote host. Trys 30 times, 30 seconds
    """
    trys = 30
    while True:
        res = copy_to_host(user, password, host, origin, destination)

        if tasks.get_return_code(res) == 0 or trys == 0:
            return res

        trys = trys - 1
        time.sleep(1)
