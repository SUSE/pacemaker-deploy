install_qdevice_packages:
    pkg.latest:
        - pkgs:
            - crmsh
            - expect
            - corosync-qdevice
