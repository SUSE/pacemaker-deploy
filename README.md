# Pacemaker cluster deployment

This project is aimed at easing the deployment of pacemaker cluster.
It does so by using two executables:
 - deploy.py, does the work using a deployment file which specifies the details of the cluster
 - wizard.py, generates a suitable deployment file aftr asking the user a number of questions
 
The deployment file can be written or edited by hand in order to use deploy.py, the use of the wizard is optional.
The deployment file is written in YAML and an example can be found in deployment.yaml.example

___
# Prerequisites

For deploying only:
 - zypper install terraform sshpass python3-Jinja2 python3-PyYAML python3-docopt

For wizard:
 - pip install inquirer
 - zypper install python3-pyfiglet python3-colorama python3-termcolor

___
# Use
- wizard.py
- deploy.py --help

The basic use is the following:
 - deploy.py create <deployment_file> -- This creates a cluster as specified in the deployment file.
 - deploy.py destroy <deployment_name> -- This destroys the cluster and erases the deployment folder. The name is the one specified in the deployment file used to create the cluster and there must a folder under deployed (deployed/<name>) which holds the data of the cluster
 
___
# Deployment file

The deployment file has the following parts:
 - name
 - provider
 - terraform
 - salt
 
Under the "terraform" ans "salt" keys, there are the following subkeys:
 - common
 - node
 - iscsi
 - monitor
 
Under the "common" key, there are generic subkeys that applies to all nodes in the cluster, be it froterrafom or salt. Same pattern follows for node, iscsi and monitor keys, where subjeys are related with data relevant for cluster generic odes, iscsi server if present and monitor server if any, respectively.

In the config/defaults.yaml file, info about all currently supported keys and educated guessed values for defaults are provided.   

Not all the keys are mandatory. The deployment file provided is mixed with the defaults config file to have a value for every single key.
This way, only keys that differ from defaults need to be specified.
Note, however, taht there are no valid defaults for some mandatory keys such as name and provider.

The defaults file is also used by the wizard to provide default values when asking the user.

___
# Architecture

The main pattern behind the project is the isolation of different concerns.
To do so, the infrastructure files are completely independent of the provisioning. In fact, they can be used directly and independently.
In the same way, dynamic provisioning can be used independently if infrastructure is already existant.
The job of deploy.py is to orchestrate both. First executing the infrastructure with the given parameters in the deployment file. Then enhances the deployment file data with the output given by the creation of then infrastructure. And finally, executes the provisioning with all the provided and gathered data. 

## Execution

 Deploy.py does its job performing the creation of the infrastructure and then the dynamic provisioning.
 The steps executed are:
  - The tool verifies if the name specified in the deployment file does already exists. Deployments are created under deployed directory, and then it is filled with all the files used to create the cluster.
  - If the deployment is not already created, the infrastructure files for the designated provider ar copied into deployment directory. The provider is also specified inthe deployment file. The infrastructure files are located under terraform/<provider>.
  - The template file for the terraform variables is rendered used the deployment file as input. That file is located under templates/<provider>/terraform.tfvars.template and is copied with the rest of infrastructure code to the deployment folder
  - Now the creation of infrastructure is executed.
  - If the infrastructure is correctly created, the ouputs generated are added to the deployment file data
  - The template files for each node for the dynamic provisioning are rendered using all the deployment data and copied to the deploymen folder. Those are located under templates/<provider>/
  - Files for the dynamic provisioning, located under salt directory, with the renderd files, are copied to each node
  - The provisioning process is executed. First in one node, that executes the init of the cluster. Then in the rest of nodes in parallel who joins
 
 ___
# TODO
 - qnetdevice infrastructure and provision
 - rest of cloud providers
 - test iscsi correctly
 - test monitor
 - verify if monitor is needed
