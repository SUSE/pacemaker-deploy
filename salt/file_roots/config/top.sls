config:
    'role:node':
        - match: grain
        - cluster_node

    'role:iscsi':
        - match: grain
        - iscsi_server

    'role:monitor':
        - match: grain
        - monitor
