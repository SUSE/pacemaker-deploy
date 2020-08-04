{% set host = grains['host'] %}
{% set init = grains['init_node'] %}

/srv/salt/copy_sshkey_qdevice:
  file.append:
    - text: |
        set node $argv
        set timeout -1
        spawn ssh-copy-id -o "StrictHostKeyChecking=no" root@$node
        expect "assword:"
        send -- "linux\r"
        expect eof

copy_sshkey_qdevice:
    cmd.run:
        - name: expect -f /srv/salt/copy_sshkey_qdevice {{grains['qdevice_ip']}}
        - require:
            - /srv/salt/copy_sshkey_qdevice        

{% if host == init %}
corosync_qdevice:
    cmd.run:
        - name: crm cluster init qdevice --qnetd-hostname={{grains['qdevice_ip']}} -y
{% endif %}