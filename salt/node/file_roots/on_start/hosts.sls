{% for name, ip in grains['host_ips'].items() %}
{{ name }}:
    host.present:
        - ip: {{ ip }}
        - names:
            - {{ name }}
{% endfor %}
