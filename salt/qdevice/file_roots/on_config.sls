include:
    - common.hostname
    - common.registration
    - common.repos
    - common.update
    - common.additional_repos
    - common.additional_pkgs
{% if grains['provider'] == 'libvirt' %}
    - common.auth_keys
    - common.ip_workaround
{% endif %}
