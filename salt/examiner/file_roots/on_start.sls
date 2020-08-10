include:
  - common.keys

install_examiner_packages:
    pkg.latest:
        - pkgs:
            - pacemaker-cts
            - pacemaker-remote
            #- python3-systemd

/root/run_tests.sh:
    file.append:
        - text: |
            /usr/share/pacemaker/tests/cts/CTSlab.py --nodes '{{grains['cluster_name']}}-node01 {{grains['cluster_name']}}-node02 {{grains['cluster_name']}}-node03' --outputfile /usr/share/pacemaker/tests/cts/cts.log --stonith-type 'fence_sbd' --stonith-args pcmk_off_action='reboot',devices='{{grains['sbd_disk_device']}}',action='reboot',sbd_path='/usr/sbin/sbd',pcmk_host_map='remote-{{grains['cluster_name']}}-node01:{{grains['cluster_name']}}-node01;remote-{{grains['cluster_name']}}-node02:{{grains['cluster_name']}}-node02;remote-{{grains['cluster_name']}}-node03:{{grains['cluster_name']}}-node03' --once --populate-resources