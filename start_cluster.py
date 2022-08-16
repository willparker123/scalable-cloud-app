import sys
import time
import logging
import yaml
import logging
from fabric import Connection, task
import os
from kubernetes import client, config
from dotenv import load_dotenv, dotenv_values
from cluster_handler import Cluster
from argparse import ArgumentParser

"""
hosts:
  52.90.32.232: 172.31.89.137
  3.86.104.131: 172.31.89.30
  54.89.180.182: 172.31.90.131
"""


def main(logger, config_env, user=None):
    if user is not None:
        main_cluster = Cluster(config_path='config.yaml', logger=logger, config_env=config_env, user=user)
    else:
        main_cluster = Cluster(config_path='config.yaml', logger=logger, config_env=config_env)
    main_cluster.start_cluster()

if __name__ == "__main__":
    # use loggers right from the start, rather than 'print'
    logger = logging.getLogger(__name__)
    # this will log boto output to std out
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    load_dotenv()
    config_env = dotenv_values(".env")
    
    parser = ArgumentParser()
    #parser.add_argument("-p", "--pipeurl", dest="pipe_url", required=True,
    #                    help="IPC, HTTP or WebSocket pipe url used to create the web3 pipe; must be supplied")
    
    main(logger, config_env)



























v1 = client.CoreV1Api()
v1.list_node() 
v1.list_namespace()
"""
returns a JSON with all the info like spec, metadata for each namespace
For eg:
{'api_version': 'v1',
 'items': [{'api_version': None,
        	'kind': None,
        	'metadata': {'annotations': None,
                     	'cluster_name': None,
                     	'creation_timestamp': datetime.datetime(2021, 2, 11, 11, 29, 32, tzinfo=tzutc()),
                     	'deletion_grace_period_seconds': None,
                     	'deletion_timestamp': None,
                     	'finalizers': None,
                     	'generate_name': None,
                     	'generation': None,
                     	'labels': None,
                     	'managed_fields': [{'api_version': 'v1',
                                         	'fields_type': 'FieldsV1',
                                         	'fields_v1': {'f:status': {'f:phase': {}}},
                                         	'manager': 'kube-apiserver',
                                         	'operation': 'Update',
                                         	'time': datetime.datetime(2021, 2, 11, 11, 29, 32, tzinfo=tzutc())}],
                     	'name': 'default',
                     	'namespace': None,
                     	'owner_references': None,
                     	'resource_version': '199',
                     	'self_link': None,
                     	'uid': '3a362d64-437d-45b5-af19-4af9ae2c75fc'},
        	'spec': {'finalizers': ['kubernetes']},
        	'status': {'conditions': None, 'phase': 'Active'}}],
'kind': 'NamespaceList',
 'metadata': {'_continue': None,
          	'remaining_item_count': None,
          	'resource_version': '69139',
          	'self_link': None}}
"""
v1.list_pod_for_all_namespaces()
v1.list_persistent_volume_claim_for_all_namespaces()

v1.list_namespaced_service(namespace="default")
v1.list_namespaced_pod(namespace="default")

metadata = client.V1ObjectMeta(name='my-app')

# We could also set fields by accessing them through instance like:
metadata.name = 'md2'

container1 = client.V1Container("my_container", "nginx")#, volume_mounts, ports)
container2 = client.V1Container("my_container_2", "npm")#, volume_mounts, ports)
containers = [container1, container2]   
pod_spec = client.V1PodSpec(containers=containers)
pod_body = client.V1Pod(metadata=metadata, spec=pod_spec, kind='Pod', api_version='v1')
pod = v1.create_namespaced_pod(namespace="default", body=pod_body)

pod_logs = v1.read_namespaced_pod_log(name="my-app", namespace="default")

v1.delete_namespaced_pod(name="my-app", namespace="default")
   
#zk_version = '3.6.3'
#jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader('etc'))
#template = jinja_environment.get_template('zoo.cfg.template')

# use loggers right from the start, rather than 'print'
logger = logging.getLogger(__name__)
# this will log boto output to std out
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

"""
hosts:
  52.90.32.232: 172.31.89.137
  3.86.104.131: 172.31.89.30
  54.89.180.182: 172.31.90.131
"""

with open('config.yaml') as f:
    config = yaml.load(f, Loader=yaml.SafeLoader)
hosts = [(h[0], h[1]) for h in config["hosts"].items()]

load_dotenv()

GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID')
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
STORAGE_BUCKET_NAME = os.getenv('STORAGE_BUCKET_NAME')

instance_count = len(hosts)

# let range run from 1 to n!
for idx in range(1, instance_count + 1):

    ip_pair = hosts[idx - 1]
    pub_ip = ip_pair[0]
    vm_user = config['vm_user']
    c = Connection(f'{vm_user}@{pub_ip}', connect_kwargs={'key_filename': config['ssh_path']})

    # with c.cd('/home/ubuntu'):
    with c.cd('~'):
        c.run(f'wget https://apache.mirrors.nublue.co.uk/zookeeper/zookeeper-{zk_version}/apache-zookeeper-{zk_version}-bin.tar.gz')

        c.run(f'tar -xzf apache-zookeeper-{zk_version}-bin.tar.gz')

    c.sudo(f'mv ~/apache-zookeeper-{zk_version}-bin /usr/local/zookeeper', warn=True)
    c.sudo('mkdir -p /var/lib/zookeeper')

    file_name = f'etc/zoo_{idx}.cfg'
    with open(file_name, 'w') as cfg_file:

        line_template = 'server.{idx}={priv_ip}:2888:3888'

        lines = []
        # let i run from 1 to n
        for i in range(1, instance_count + 1):
            priv_ip = hosts[i - 1][1]
            lines.append(line_template.format(idx=i, priv_ip=priv_ip if i is not idx else '0.0.0.0'))

        server_list = "\n".join(lines)

        cfg_file.write(template.render(server_list=server_list))

    c.put(local=file_name, remote="zoo.cfg")
    c.sudo('cp ~/zoo.cfg /usr/local/zookeeper/conf/zoo.cfg')
    c.sudo(f'echo {idx} | sudo tee -a /var/lib/zookeeper/myid')
    c.sudo(f'apt-get update')

    c.sudo(f'apt install -y openjdk-11-jdk')

    c.run('export JAVA_HOME=/usr/lib/jvm/java-1.11.0-openjdk-amd64')
    c.sudo('/usr/local/zookeeper/bin/zkServer.sh start')
