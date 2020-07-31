{% if grains['additional_packages'] is defined and grains['additional_packages'] %}
install_additional_pkgs:
    pkg.latest:
        - pkgs:
{% for package in grains['additional_pkgs'] %}
            - {{ package }}
{% endfor %}
{% endif %}
