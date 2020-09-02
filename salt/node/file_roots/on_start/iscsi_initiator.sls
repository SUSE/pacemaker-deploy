open-iscsi:
    pkg.installed:
        - retry:
            attempts: 3
            interval: 15

# lsscsi is used to retrieve the sbd disk in the automatic pillar files
lsscsi:
    pkg.installed:
        - retry:
            attempts: 3
            interval: 15

{% if grains['osrelease_info'][0] >= 15 and (grains['osrelease_info']|length > 1 and grains['osrelease_info'][1] >= 2) %}
# We cannot use service.running as this systemd unit will stop after being executed
# It is used only to create the initiatorname.iscsi file
start_iscsi_init:
    module.run:
        - service.start:
            - name: iscsi-init
{% endif %}

/etc/iscsi/initiatorname.iscsi:
    file.replace:
        - pattern: "^InitiatorName=.*"
        - repl: "InitiatorName=iqn.{{ grains['server_id'] }}.suse.qa"

/etc/iscsi/iscsid.conf:
    file.replace:
        - pattern: "^node.startup = manual"
        - repl: "node.startup = automatic"

iscsi-queue-depth:
    file.replace:
        - name: "/etc/iscsi/iscsid.conf"
        - pattern: "^node.session.queue_depth = [0-9]*"
        - repl: "node.session.queue_depth = 64"

iscsi:
    service.running:
        - enable: True
        - watch:
            - file: /etc/iscsi/iscsid.conf
            - file: /etc/iscsi/initiatorname.iscsi

iscsi_discovery:
    cmd.run:
        - name: until iscsiadm -m discovery -t st -p "{{ grains['iscsi_ip'] }}:3260" -l -o new;do sleep 10;done
        - output_loglevel: quiet
        - hide_output: True
        - timeout: 2400
        - require:
            - iscsi

iscsid:
    service.running:
        - watch:
            - cmd: iscsi_discovery
