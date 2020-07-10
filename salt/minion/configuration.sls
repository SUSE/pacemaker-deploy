copy_grains:
    file.copy:
        - name: /etc/salt/grains
        - source: /tmp/grains

backup_salt_configuration:
    file.copy:
        - name: /etc/salt/minion.backup
        - source: /etc/salt/minion

configure_file_roots:
    file.append:
        - name: /etc/salt/minion
        - text: |
            file_roots:
                generic:
                    - /srv/salt/generic
                    - /usr/share/salt-formulas/states
                config:
                    - /srv/salt/config
                    - /usr/share/salt-formulas/states
                base:
                    - /srv/salt/base
                    - /usr/share/salt-formulas/states

            pillar_roots:
                generic:
                    - /srv/pillar/generic
                config:
                    - /srv/pillar/config
                base:
                    - /srv/pillar/base

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
