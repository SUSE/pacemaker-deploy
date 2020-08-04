{% if grains['additional_repos'] is defined %}
{% set sle_version = 'SLE_'~grains['osrelease_info'][0] %}
{% set sle_version = sle_version~'_SP'~grains['osrelease_info'][1] if grains['osrelease_info']|length > 1 else sle_version %}
{% for label, url in grains['additional_repos'].items() %}
    {% if label == 'ha' and 'SLE_' not in url %}
        {% set repository = url~"/"~sle_version %}
    {% else %}
        {% set repository = url %}
    {% endif %}
{{ label }}_repo:
    pkgrepo.managed:
        - humanname: {{ label }}
        - baseurl: {{ repository }}
        - gpgautoimport: True
        - priority: 90
        - refresh: True
        - retry:
            attempts: 3
            interval: 15
{% endfor %}
{% endif %}