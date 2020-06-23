{% if grains['additional_packages'] is defined %}
install_additional_packages:
    pkg.latest:
        - pkgs:
{% for package in grains['additional_packages'] %}
            - {{ package }}
{% endfor %}
{% endif %}
