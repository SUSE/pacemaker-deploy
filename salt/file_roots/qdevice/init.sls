install_qnetd_packages:
    pkg.latest:
        - pkgs:
            - corosync-qnetd
