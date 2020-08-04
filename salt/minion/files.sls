create_salt_folder:
    file.directory:
        - name: /srv/salt
        - user: root
        - mode: "0755"
        - makedirs: True

populate_salt_folder:
    file.recurse:
        - name: /srv/salt
        - source: salt://file_roots
        - include_empty: True
