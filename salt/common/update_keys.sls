{% if "azure" == grains['provider'] %}
{% set host = grains['host'] %}
{% set username = grains['usernames'][host] %}

update_sshkeys:
    cmd.run:
        - name: sudo cp /home/{{username}}/.ssh/authorized_keys /root/.ssh/authorized_keys
        - stateful: True

{% endif %}