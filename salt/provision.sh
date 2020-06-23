#!/bin/bash -xe
# Script to provision the machines using salt. It provides different stages to install and
# configure salt and run different salt executions. Find more information in print_help method
# or running `sh provision.sh -h`

get_grain () {
    re="$1:\s*(.*)"
    grains_file=$2
    grains_file=${grains_file:="/etc/salt/grains"}
    grains_content=$(grep -E $re $grains_file)
    if [[ $grains_content =~ $re ]]; then
        echo ${BASH_REMATCH[1]};
        return 0
    else
        return 1
    fi
}

salt_output_colored () {
    if [[ "$(get_grain qa_mode)" == "true" ]]; then
        echo "--no-color"
    else
        echo "--force-color"
    fi
}

install_salt_minion () {
    reg_code=$1
    # If required, register
    if [[ $reg_code != "" ]]; then
        # Check SLE version
        source /etc/os-release
        # Register the system on SCC
        SUSEConnect -r "$reg_code"

        # Register the modules accordingly with the SLE version.
        if [[ $VERSION_ID =~ ^12\.? ]]; then
            SUSEConnect -p sle-module-adv-systems-management/12/x86_64
        elif [[ $VERSION_ID =~ ^15\.? ]]; then
            SUSEConnect -p sle-module-basesystem/$VERSION_ID/x86_64
        else
            echo "SLE Product version not supported by this script. Please, use version 12 or higher."
            exit 1
        fi
    fi

    # We have to force refresh the repos and the keys (keys may change during lifetime of this OS/image)
    zypper --non-interactive --gpg-auto-import-keys refresh --force --services
    zypper --non-interactive install salt-minion

    # Deregister
    if [[ $reg_code != "" ]]; then
       SUSEConnect -d
    fi
}

bootstrap_salt () {
    mv /tmp/salt /root || true

    # Get registration code
    reg_code=$(get_grain reg_code /tmp/grains)
    # Check if salt-call is installed
    which salt-call > /dev/null 2>&1 && salt_installed=1

    # Workaround for the cases where the cloud providers are coming without repositories
    # https://www.suse.com/support/kb/doc/?id=7022311
    # Check if the deployment is executed in a cloud provider
    [[ "$(get_grain provider /tmp/grains)" =~ aws|azure|gcp ]] && cloud=1
    if [[ ${cloud} == 1 && "${reg_code}" == "" ]]; then
        zypper lr || sudo /usr/sbin/registercloudguest --force-new
    fi

    # Install salt if not already installed
    if [[ ${salt_installed} != 1 ]]; then
        install_salt_minion ${reg_code}
    fi

    # Recheck if salt-call is installed. If it's not available stop execution
    which salt-call || exit 1
    # Move salt grains to salt folder
    mkdir -p /etc/salt;mv /tmp/grains /etc/salt || true
}

config () {
    salt-call \
        --local \
        --file-root=/root/salt/state \
        --pillar-root=/root/salt/pillar \
        --log-level=info \
        --log-file=/var/log/salt-config.log \
        --log-file-level=debug \
        --retcode-passthrough \
        $(salt_output_colored) \
        state.highstate || exit 1
}

fire () {
	salt-call \
        --local \
        --log-level=info \
        --log-file=/var/log/salt-fire.log \
        --log-file-level=debug \
        --retcode-passthrough \
        $(salt_output_colored) \
        state.highstate saltenv=base || exit 1
}

print_help () {
    cat <<-EOF
Provision the machines. The provisioning has different steps, so they can be executed depending on
the selected flags. The actions are always executed in the same order (if multiple are selected),
from top to bottom in this help text.

Supported Options (if no options are provided (excluding -l) all the steps will be executed):
  -s               Bootstrap salt installation and configuration. It will register to SCC channels if needed
  -c               Execute predeployment operations (update hosts and hostnames, install support packages, etc)
  -f               Execute deployment operations (fire up corosync, pacemaker, etc)
  -l [LOG_FILE]    Append the log output to the provided file
  -h               Show this help.
EOF
}

argument_number=0
while getopts ":hscfl:" opt; do
    argument_number=$((argument_number + 1))
    case $opt in
        h)
            print_help
            exit 0
            ;;
        s)
            execute_bootstrap_salt=1
            ;;
        c)
            execute_config=1
            ;;
        f)
            execute_fire=1
            ;;
        l)
            log_to_file=$OPTARG
            ;;
        *)
            echo "Invalid option -$OPTARG" >&2
            print_help
            exit 1
            ;;
    esac
done

if [[ -n $log_to_file ]]; then
    argument_number=$((argument_number - 1))
    exec 1>> $log_to_file
fi

if [ $argument_number -eq 0 ]; then
    bootstrap_salt
    config
    fire
else
    [[ -n $execute_bootstrap_salt ]] && bootstrap_salt
    [[ -n $execute_config ]] && config
    [[ -n $execute_fire ]] && fire
fi
exit 0
