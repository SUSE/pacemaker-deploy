install_qdevice_packages:
    pkg.latest:
        - pkgs:
            - crmsh
            - corosync-qdevice
