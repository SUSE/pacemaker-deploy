import subprocess


def run(command, input = ""):
    """
    Executes a given command. Return a tuple with (return_code, stdout, stderr)
    """
    if input != "":
        pipes = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = pipes.communicate(input=input.encode('utf-8'))
    else:
        pipes = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        stdout, stderr = pipes.communicate()
    
    return (pipes.returncode, stdout.decode("utf-8"), stderr.decode("utf-8"))


#
# Constructors
#
def success(message = ""):
    """
    Result constructor to indicate a success operation
    """
    return (0, message, "")


def failure(message = ""):
    """
    Result constructor to indicate a failed operation
    """
    return (1, "", message)


#
# Accessors
#
def get_return_code(result):
    return_code, _, _ = result
    return return_code


def get_stdout(result):
    _, stdout, _ = result
    return stdout


def get_stderr(result):
    _, _, stderr = result
    return stderr


#
# Predicates
#
def has_succeeded(result):
    return get_return_code(result) == 0


def has_failed(result):
    return not has_succeeded(result)

