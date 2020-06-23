include:
{% if grains['provider'] in ['aws', 'azure', 'gcp'] %}
    - cluster_node.network
{% endif %}
    - cluster_node.hosts
    - cluster_node.cluster_packages
{% if grains['cluster_ssh_pub'] is defined and grains['cluster_ssh_key'] is defined %}
    - cluster_node.ssh
{% endif %}
{% if grains['shared_storage_type'] == 'iscsi' %}
    - cluster_node.iscsi_initiator
{% endif %}
    - cluster_node.setup
{% if grains.get('monitor_enabled') %}
    - cluster_node.monitor
{% endif %}
{%- if grains['provider'] == 'aws' %}
    - cluster_node.aws_add_credentials
    - cluster_node.aws_data_provider
{%- endif %}
  