{% if grains['additional_repos'] is defined %}
{% for label, url in grains['additional_repos'].items() %}
{{ label }}_repo:
    pkgrepo.managed:
        - humanname: {{ label }}
        - baseurl: {{ url }}
        - gpgautoimport: True
        - priority: 90
        - refresh: True
        - retry:
            attempts: 3
            interval: 15
{% endfor %}
{% endif %}