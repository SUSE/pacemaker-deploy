{% if grains['authorized_keys'] is defined %}
authorized_keys:
    file.append:
        - name: /root/.ssh/authorized_keys
        - text:
{% for key in grains['authorized_keys'] %}
            - {{ key }}
{% endfor %}
        - makedirs: True
{% endif %}
