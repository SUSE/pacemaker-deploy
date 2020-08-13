# Pacemaker cluster deployment

This project is aimed at easing the deployment of pacemaker cluster.
It does so by using two executables:

- ```deploy.py``` does the work using a deployment file which specifies the details of the cluster
- ```wizard.py``` generates a suitable deployment file aftr asking the user a number of questions

The deployment file can be written or edited by hand in order to use ```deploy.py```, the use of the wizard is optional.
The deployment file is written in YAML and an example can be found in [deployment.yaml.example](deployment.yaml.example)

# Prerequisites

- ```zypper install terraform sshpass python3-Jinja2 python3-PyYAML python3-docopt```

# Use

- ```deploy.py --help```

For a quickstart use:
```./deploy.py create deployment.yaml.example```
For more info check the [deployment example file](deployment.yaml.example)

The basic use is the following:

- ```deploy.py create DEPLOYMENT_FILE``` - This creates a cluster as specified in the deployment file.
- ```deploy.py destroy DEPLOYMENT_FILE``` - This destroys the cluster and erases the deployment folder. The name is the one specified in the deployment file used to create the cluster and there must a folder under deployed (deployed/DEPLOYMENT_NAME) which holds the data of the cluster

# Deployment file

The deployment file has the following parts:

- name
- provider
- common
- node
- iscsi
- sbd
- qdevice
- examiner

Under the __common__ key, there are generic subkeys that applies to all nodes in the cluster. Same pattern follows for node, iscsi, sbd, qdevice and examiner keys, where subkeys are related with data relevant for cluster generic nodes, iscsi server if present, shared-disk if present, qdevice if present and examiner server if any, respectively.

In the config/defaults.yaml file, info about all currently supported keys and educated guessed values for defaults are provided.

More concrete keys override more generic ones. For example if ```volume_name``` is specified under __common__ key, and ```examiner``` specifies under its key another different value, this last value is the one applied to ```examiner``` server. For the rest of machines in the cluster, supposing no other keys overrides ```volume_name``` value, the __common__ value will be used. The same pattern applies to cluster nodes themselves (under __node__ key), where you can override keys for a specific machine specifying its number as key under __node__, ie:
```
node:
    volume_name: os_image
    1:
        volume_name: other_os_image
```
In this case all cluster nodes will use ```os_image``` except node number 1 which will use ```other_os_image```.

The keys currently available to be overriden are:
 - source_image
 - volume_name
 - additional_repos
 - additional_pkgs
 - cpus
 - memory
 - disk_size

Not all the keys are mandatory, as can be seen in the [example deployment file](deployment.yaml.example). The deployment file provided is mixed with the [defaults config file](config/defaults.yaml) to have a value for every single key.
This way, only keys that differ from defaults need to be specified.
Note, however, that there are no valid defaults for some mandatory keys such as ```name``` and ```provider```.

The [defaults file](config/defaults.yaml) is also used by the wizard to provide default values when asking the user.

# Architecture

The main pattern behind the project is the isolation of different concerns.
To do so, the infrastructure files are completely independent of the provisioning. In fact, they can be used directly and independently.
In the same way, dynamic provisioning can be used independently if infrastructure is already existant.
The job of ```deploy.py``` is to orchestrate both. First executing the infrastructure with the given parameters in the deployment file. Then enhances the deployment file data with the output given by the creation of then infrastructure. And finally, executes the provisioning with all the provided and gathered data.

## Execution

 ```deploy.py``` does its job performing the creation of the infrastructure and then the dynamic provisioning.
 The steps executed are:

- The tool verifies if the name specified in the deployment file does already exists. Deployments are created under deployed directory, and then it is filled with all the files used to create the cluster.
- If the deployment is not already created, the infrastructure files for the designated provider are rendered into deployment directory. The provider is also specified in the deployment file. The infrastructure files are located under terraform/PROVIDER.
- Now the creation of infrastructure is executed.
- If the infrastructure is correctly created, the ouputs generated are added to the deployment file data
- The template files for each node for the dynamic provisioning are rendered using all the deployment data and copied to the deployment folder. Those are located under salt/grains.j2
- Files for the dynamic provisioning, located under salt directory, with the rendered files, are copied to each node
- The provisioning process is executed.


# TODO

- rest of cloud providers
