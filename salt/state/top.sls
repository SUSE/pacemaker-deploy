base:
    'role:node':
        - match: grain
        - os_setup
        - default
        - cluster_node

    'role:monitor':
        - match: grain
        - os_setup
        - default
        - monitor
