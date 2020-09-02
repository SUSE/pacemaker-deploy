copy_grains:
    file.copy:
        - name: /etc/salt/grains
        - source: /tmp/salt/grains

backup_salt_configuration:
    file.copy:
        - name: /etc/salt/minion.backup
        - source: /etc/salt/minion

configure_file_roots:
    file.append:
        - name: /etc/salt/minion
        - text: |
            file_roots:
                config:
                    - /srv/salt
                    - /usr/share/salt-formulas/states
                rendezvous:
                    - /srv/salt
                    - /usr/share/salt-formulas/states
                base:
                    - /srv/salt
                    - /usr/share/salt-formulas/states

            pillar_roots:
                config:
                    - /srv/pillar
                rendezvous:
                    - /srv/pillar
                base:
                    - /srv/pillar

# Old module.run style will be deprecated after sodium release
upgrade_module_run:
    file.append:
        - name: /etc/salt/minion
        - text:
            - 'use_superseded:'
            - '- module.run'

minion_service:
    service.dead:
        - name: salt-minion
        - enable: False
