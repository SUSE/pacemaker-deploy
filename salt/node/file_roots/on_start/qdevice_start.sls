{% set host = grains['host'] %}
{% set init = grains['init_node'] %}

{% if host == init %}
corosync_qdevice:
    cmd.run:
        - name: crm cluster init qdevice --qnetd-hostname={{grains['qdevice_name'] }} -y
        - retry:
            attempts: 30
            interval: 10        
{% endif %}