# set the hostname in the kernel, this is needed for Red Hat systems
# and does not hurt in others
kernel_hostname:
    cmd.run:
        - name: sysctl kernel.hostname={{ grains['host'] }}
        - unless: sysctl --values kernel.hostname | grep -w {{ grains['host'] }}

# set the hostname in userland. There is no consensus among distros
# but Debian prefers the short name, SUSE demands the short name,
# Red Hat suggests the FQDN but works with the short name.
# Bottom line: short name is used here
temporary_hostname:
    cmd.run:
{% if grains['init'] == 'systemd' %}
        - name: hostnamectl set-hostname {{ grains['host'] }}
{% else %}
        - name: hostname {{ grains['host'] }}
{% endif %}

# set the hostname in the filesystem, matching the temporary hostname
permanent_hostname:
    file.managed:
        - name: /etc/hostname
        - contents: {{ grains['host'] }}

# /etc/HOSTNAME is supposed to always contain the FQDN
legacy_permanent_hostname:
    file.managed:
        - name: /etc/HOSTNAME
        - follow_symlinks: False
        - contents: {{ grains['host'] }}.{{ grains['network_domain'] }}
