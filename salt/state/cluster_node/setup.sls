/srv/pillar:
    file.directory:
        - user: root
        - mode: "0755"
        - makedirs: True

/srv/salt/top.sls:
    file.copy:
        - source: /root/salt/files/state/top.sls

/srv/pillar/top.sls:
    file.copy:
        - source: /root/salt/files/pillar/top.sls

/srv/pillar/cluster.sls:
    file.copy:
        - source: /root/salt/files/pillar/cluster.sls
