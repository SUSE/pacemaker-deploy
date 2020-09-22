create_ssh_folder:
    file.directory:
        - name: /root/.ssh
        - user: root
        - mode: "0755"
        - makedirs: True

populate_ssh_folder:
    file.recurse:
        - name: /root/.ssh
        - source: salt://key
        - include_empty: True
        - file_mode: "0600"

populate_ssh_authorized_keys:
    cmd.run:
        - name: |
            cat /root/.ssh/id_rsa.pub >> /root/.ssh/authorized_keys
