include:
{% if grains['provider'] in ['aws', 'azure', 'gcp'] %}
    - on_start.network
{% endif %}
    - on_start.hosts
{% if grains['cluster_ssh_pub'] is defined and grains['cluster_ssh_key'] is defined %}
    - on_start.ssh
{% endif %}
{% if grains['shared_storage_type'] == 'iscsi' %}
    - on_start.iscsi_initiator
{% endif %}
{%- if grains['provider'] == 'aws' %}
    - on_start.aws_add_credentials
    - on_start.aws_data_provider
{%- endif %}
{% if grains['qdevice_enabled'] %}
    - on_start.qdevice_setup
{% endif %}
    - cluster
{% if grains['qdevice_enabled'] %}
    - on_start.qdevice_start
{% endif %}
