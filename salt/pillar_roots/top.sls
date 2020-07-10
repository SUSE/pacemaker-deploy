base:
    'role:node':
        - match: grain
        - cluster

    'role:iscsi':
        - match: grain
        - iscsi_server
