base:
    'role:node':
        - match: grain
        - cluster_node
        - cluster
{% if grains['qdevice_enabled'] %}
        - cluster_node.qdevice_start
{% endif %}


    'role:iscsi':
        - match: grain
        - iscsi_server

    'role:monitor':
        - match: grain
        - monitor

    'role:qdevice':
        - match: grain
        - qdevice

config:
    '*':
        - common
