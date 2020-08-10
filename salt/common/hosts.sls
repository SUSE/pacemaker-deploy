{% for name, ip in grains['machines'].items() %}
{{ name }}:
    host.present:
        - ip: {{ ip }}
        - names:
            - {{ name }}
{% endfor %}
