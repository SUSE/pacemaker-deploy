include:
    - common.update_keys
{% if grains['provider'] in ['aws', 'azure', 'gcp'] %}
    - on_start.network
{% endif %}
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
    - cluster
{% if grains['examiner_enabled'] %}
    - on_start.examiner
{% endif %}
