include:
    - common.hostname
    - common.registration
    - common.repos
    - common.update
    - common.additional_repos
{% if grains['shared_storage_type'] == 'iscsi' %}
    - common.iscsi
{% endif %}
    - common.additional_pkgs
{% if grains['provider'] == 'libvirt' %}
    - common.auth_keys
    - common.ip_workaround
{% endif %}
    - common.add_pillar_files
