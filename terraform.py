import os

import tasks


def is_initialized(path):
    """
    Check if Terraform is initialized in a given path.
    """
    return os.path.exists(f"{path}/.terraform")


def init(path):
    """
    Initialize Terraform in a given path.
    """
    if not is_initialized(path):
        return tasks.run(f"cd {path} && terraform init -no-color")
    return tasks.success()


def workspace(path, workspace):
    """
    Switch to a new Terraform workspace.
    """
    return tasks.run(f"cd {path} && terraform workspace new {workspace} -no-color")


def apply(path):
    """
    Launch Terraform and apply the changes.
    """
    return tasks.run(f"cd {path} && terraform apply -auto-approve -no-color")


def refresh(path):
    """
    Launch Terraform and refresh output.
    """
    return tasks.run(f"cd {path} && terraform refresh")
    

def destroy(path):
    """
    Launch Terraform and eliminate all infrastructure.
    """
    return tasks.run(f"cd {path} && terraform destroy -auto-approve -no-color")


def output(path):
    """
    Get Terraform output as json
    """
    return tasks.run(f"cd {path} && terraform output -json")
