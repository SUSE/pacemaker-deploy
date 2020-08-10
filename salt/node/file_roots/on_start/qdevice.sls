{% set host = grains['host'] %}
{% set init = grains['init_node'] %}

install_qdevice_packages:
    pkg.latest:
        - pkgs:
            - corosync-qdevice

{% if host == init %}
corosync_qdevice:
    cmd.run:
        #- name: crm cluster init qdevice --qnetd-hostname={{grains['qdevice_ip']}} -y
        - name: crm cluster init qdevice --qnetd-hostname={{grains['qdevice_name' }} -y
{% endif %}