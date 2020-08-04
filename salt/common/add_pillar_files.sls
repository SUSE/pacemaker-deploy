create_pillar_folder:
    file.directory:
        - name: /srv/pillar
        - user: root
        - mode: "0755"
        - makedirs: True

populate_pillar_folder:
    file.recurse:
        - name: /srv/pillar
        - source: salt://pillar_roots
        - include_empty: True
