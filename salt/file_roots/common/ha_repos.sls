{% if 'SLE_' in grains['ha_repo'] %}
{% set repository = grains['ha_repo'] %}
{% else %}
{% set sle_version = 'SLE_'~grains['osrelease_info'][0] %}
{% set sle_version = sle_version~'_SP'~grains['osrelease_info'][1] if grains['osrelease_info']|length > 1 else sle_version %}
{% set repository = grains['ha_repo']~"/"~sle_version %}
{% endif %}

ha-factory-repo:
    pkgrepo.managed:
        - name: ha-factory
        - baseurl: {{ repository }}
        - gpgautoimport: True
        - priority: 90
        - refresh: True
        - retry:
            attempts: 3
            interval: 15
