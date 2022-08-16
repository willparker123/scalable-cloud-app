import yaml
import os
import logging
import time
import sys
from instance_handler import terminate_instances, get_join_token, create_instance_autoscaling_group, valid_instance_group_nodetypes
from kubernetes_interaction import Kubernetes_Interaction
from dotenv import load_dotenv, dotenv_values
from fabric import Connection
from helpers import fixpath
import invoke

class Cluster(object):
    def __init__(self, config_path='config.yaml', logger=None, config_env=None, user=None):
        self.config_path = config_path
        self.config = self.load_config(config_path)
        self.hosts = self.load_hosts(config_path)
        self.context = invoke.context.Context()
        self.valid_instance_group_nodetypes = valid_instance_group_nodetypes
        load_dotenv()
        l = None
        if logger is not None:
            l = logger
        else:
            l = logging.getLogger(__name__)
            logging.basicConfig(stream=sys.stdout, level=logging.INFO)
        self.logger = l
        if config_env is not None:
            self.config_env = config_env
        else:
            self.config_env = dotenv_values(".env")
        if user is not None:
            self.user = user
        else:
            self.user = self.config["sca_user"]
        
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
        try:
            hosts = [(h[0], h[1]) for h in config["hosts"].items()]
        except:
            hosts = []
        return hosts
    
    def get_new_hosts(self, hosts=None, fresh_hosts=None, aws_instancename="aws_asg_k8scp", instance_nodetype="kubernetes_worker", aws_instancetype="ec2", aws_image_id="ami-05e4673d4a28889fe", aws_az_region="us-east-1a", securitygroup=None, template_name="ec2_launch_template_k8scp"):
        fs = self.fresh_hosts
        if fresh_hosts is not None:
            fs = fresh_hosts
        hs = self.hosts
        if hosts is not None:
            hs = hosts
            
        if fs:
            #GET NEW HOSTS IN AWS ASG
            self.config["hosts"] = {}
            with open("config.yaml", 'w') as f:
                try:
                    yaml.dump(self.config, f, default_flow_style=False)
                except yaml.YAMLError as exception:
                    self.logger.warning(exception)
                    raise ValueError("Error: could not open 'config.yaml'")
            updated_hosts, ids, pubips, privips = create_instance_autoscaling_group(self.context, self.config, self.config_env, self.logger, instance_name=aws_instancename, instance_nodetype=instance_nodetype, instance_type=aws_instancetype, 
                                                                group_name=aws_instancename, template_name=template_name, image_id=aws_image_id, az_region=aws_az_region, securitygroup=securitygroup)
            for uh in updated_hosts:
                self.config["hosts"][uh[0]] = uh[1]
            with open("config.yaml", 'w') as f:
                try:
                    yaml.dump(self.config, f, default_flow_style=False)
                except yaml.YAMLError as exception:
                    self.logger.warning(exception)
                    raise ValueError("Error: could not open 'config.yaml'")
            if ids is None and updated_hosts is None and pubips is None and privips is None:
                raise ValueError("Error: get_new_hosts failed on create_instance_autoscaling_group")
            aws_asg = [{'id': ids[i], 'host': (pubips[i], privips[i])} for i in range(len(ids))]
            print(f"New AWS Autoscaling Group: {aws_asg}")
            newhosts = []
            for host in updated_hosts:
                newhosts.append((host[0], host[1]))
            return newhosts, aws_asg
        else:
            newhosts = []
            for host in hs:
                newhosts.append((host[0], host[1]))
            return newhosts, None

    def stop_cluster(self):      
        for instance_type in self.valid_instance_group_nodetypes:
            terminate_instances(f'asg_{instance_type}')
            
    def start_cluster(self, hosts=None, config_path=None, replicate_az=False):
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
        tempname = "k8scp"
        k8scp_image_id = "ami-05e4673d4a28889fe"
        az_pref = config["aws_azs"][0]
        instance_nodetype = "kubernetes_controlplane"
        if replicate_az:
            for i, az in enumerate(config["aws_azs"].items()):
                new_hosts, aws_asg = self.get_new_hosts(hosts_, self.fresh_hosts, aws_instancename=f"aws_asg_{tempname}_{i}", instance_nodetype=instance_nodetype, aws_instancetype="ec2", aws_image_id=k8scp_image_id, aws_az_region=az, securitygroup=None, template_name=f"ec2_launch_template_{tempname}_{i}")
        else:
            new_hosts, aws_asg = self.get_new_hosts(hosts_, self.fresh_hosts, aws_instancename=f"aws_asg_{tempname}", instance_nodetype=instance_nodetype, aws_instancetype="ec2", aws_image_id=k8scp_image_id, aws_az_region=az_pref, securitygroup=None, template_name=f"ec2_launch_template_{tempname}")
        #TODO RUN K8S CONTROLPLANE, INIT AND SCALE TO AWS_ASG
        print(new_hosts)
        creds = new_hosts[0]
        user, host = creds[0], creds[1]
        self.logger.info(f"Trying connection to {user}@{host}...")
        con = Connection(f"{user}@{host}")
        token = get_join_token(con, self.logger)
        interaction = Kubernetes_Interaction(token)
        podsList = interaction.list_pods()
        self.logger.info(podsList)
        
        #instancename_k8scp = "aws_asg_k8scp"
        #updated_hosts, ids, pubips, privips = create_instance_autoscaling_group(self.config, self.logger, instance_name=instancename_k8scp, instance_type="kubernetes-controlplane", 
        #                                                    group_name=None, template_name="ec2_launch_template", image_id="ami-05e4673d4a28889fe", az_region="us-east-1a", securitygroup=None)
        #aws_asg_k8scp = [{'id': ids[i], 'host': (pubips[i], privips[i])} for i in range(len(ids))]
        #return aws_asg_k8scp
        
        
        
        instancename_k8scp = "aws_asg_k8sw"
        
        
        
        file = "application.yaml"
        interaction.apply_resource(file)
        time.sleep(5)