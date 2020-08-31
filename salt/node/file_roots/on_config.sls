include:
    - common.hostname
    - common.registration
    - common.repos
    - common.additional_repos
    - common.update
{% if grains['shared_storage_type'] == 'iscsi' %}
    - common.iscsi
{% endif %}
    - common.habootstrap
    - common.additional_pkgs
{% if grains['provider'] == 'libvirt' %}
    - common.auth_keys
    - common.ip_workaround
{% endif %}
    - common.hosts
    - common.keys    
    - common.add_pillar_files
