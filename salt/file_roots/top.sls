base:
    'role:node':
        - match: grain
        - cluster_node
        - cluster

    'role:iscsi':
        - match: grain
        - iscsi_server

    'role:monitor':
        - match: grain
        - monitor

config:
    '*':
        - common
