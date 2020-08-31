include:
    - common.update_keys

install_qnetd_packages:
    pkg.latest:
        - pkgs:
            - corosync-qnetd

customize_corosync_qnetd:
    file.replace:
        - name: '/etc/sysconfig/corosync-qnetd'
        - pattern: '^COROSYNC_QNETD_OPTIONS=""$'
        - repl: 'COROSYNC_QNETD_OPTIONS="{{grains['qdevice_options']}}"'

corosync_qnetd_service:
    service.running:
        - name: corosync-qnetd
        - restart: True
