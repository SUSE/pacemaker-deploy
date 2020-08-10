{% set me = grains['host_ip'] %}

install_keys_packages:
    pkg.latest:
        - pkgs:
            - expect

create_ssh_key:
  cmd.run:
    - name: yes y | sudo ssh-keygen -f /root/.ssh/id_rsa -C '{{grains["host"]}}' -N ''

{% for name, ip in grains['machines'].items() if ip != me %}
/srv/salt/copy_sshkey_to_{{ name }}:
    file.append:
        - text: |
            set node $argv
            set timeout -1
            spawn ssh-copy-id -o "StrictHostKeyChecking=no" root@$node
            expect "assword:"
            send -- "linux\r"
            expect eof

copy_sshkey_to_{{ name }}:
    cmd.run:
        #- name: expect -f /srv/salt/copy_sshkey_to_{{ name }} {{ ip }}
        - name: expect -f /srv/salt/copy_sshkey_to_{{ name }} {{ name }}
        - require:
            - /srv/salt/copy_sshkey_to_{{ name }}
{% endfor %}
