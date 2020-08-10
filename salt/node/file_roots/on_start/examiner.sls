install_examiner_packages:
    pkg.latest:
        - pkgs:
            - pacemaker-cts
            - pacemaker-remote


sbd_remote:
    service.enabled:
        - name: sbd_remote
