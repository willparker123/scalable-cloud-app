import yaml
import os
import logging
import time
import sys
from instance_handler import terminate_instances, get_join_token
from kubernetes_interaction import Kubernetes_Interaction
from dotenv import load_dotenv, dotenv_values
from fabric import Connection
from helpers import fixpath

class Cluster(object):
    def __init__(self, config_path='config.yaml', logger=None, config_env=None, user=None):
        self.config_path = config_path
        self.config = self.load_config(config_path)
        self.hosts = self.load_hosts(config_path)
        load_dotenv()
        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)
            logging.basicConfig(stream=sys.stdout, level=logging.INFO)
        if config_env is not None:
            self.config_env = config_env
        else:
            self.config_env = dotenv_values(".env")
        if user is not None:
            self.user = user
        else:
            if self.config_env["SCA_USER"] is None:
                logger.warning(f"   *** Environment variable 'SCA_USER' is not set; using cluster.user='root' ***")
                self.user = self.config["vm_user"]
            else:
                self.user = self.config_env["SCA_USER"]
        
    def load_config(self, path=None):
        p = self.config_path
        if path is not None:
            p = path
        p = f"{fixpath(os.getcwd())}\{p}"
        if not os.path.exists(p):
            raise ValueError(f"Error: config file '{p}' is missing")
        with open(p) as f:
            try:
                config = yaml.load(f, Loader=yaml.SafeLoader)
                return config
            except:
                raise ValueError(f"Error: could not load '{p}'")
    
    def load_hosts(self, path=None):
        p = self.config_path
        if path is not None:
            p = path
        config = self.load_config(p)
        hosts = [(k, v) for k, v in config['hosts'].items()]
        return hosts
    
    def get_new_hosts(self, hosts=None, fresh_hosts=None):
        fs = self.fresh_hosts
        if fresh_hosts is not None:
            fs = fresh_hosts
        hs = self.hosts
        if hosts is not None:
            hs = hosts
            
        newhosts = []
        if fs:
            #TODO GET NEW HOSTS
            #TODO GET NEW HOSTS
            #TODO GET NEW HOSTS
            raise ValueError("TODO GET NEW HOSTSTODO GET NEW HOSTSTODO GET NEW HOSTSTODO GET NEW HOSTSTODO GET NEW HOSTS")
        else:
            for host in hs:
                (pub_ip, priv_ip) = host
                newhosts.append((pub_ip, priv_ip))
        return newhosts

    def stop_cluster(self):      
        for instance_type in self.valid_instance_group_types:
            terminate_instances(f'asg_{instance_type}')
            
    def start_cluster(self, hosts=None, config_path=None):
        p_config = self.config_path
        if config_path is not None:
            p_config = config_path
        config = self.load_config(p_config)
        hosts_ = self.load_hosts(p_config)
        if hosts is not None:
            hosts_ = hosts
        
        new_hosts = hosts_
        fresh_hosts = False
        if len(hosts_) == 1 and hosts_[0] == ("1.2.3.4", "5.6.7.8"):
            fresh_hosts = True
            p = f"{fixpath(os.getcwd())}\{p_config}"
            self.logger.warning(f"   hosts in '{p}' is 1.2.3.4:5.6.7.8 - creating EC2 instances from scratch; if you would like to use existing hosts, please edit '{p}'")
        self.fresh_hosts = fresh_hosts
        new_hosts = self.get_new_hosts(hosts_, fresh_hosts)

        creds = new_hosts[0]
        (user, host) = creds
        con = Connection(f"{user}@{host}")
        token = get_join_token(con)
        interaction = Kubernetes_Interaction(token)
        podsList = interaction.list_pods()
        self.logger.info(podsList)

        file = "application.yaml"
        interaction.apply_resource(file)
        time.sleep(5)