import sys
import time

import yaml
import boto3
import base64
import logging
from fabric import task, Connection
from botocore.exceptions import ClientError
from contextlib import redirect_stdout

# use loggers right from the start, rather than 'print'
logger = logging.getLogger(__name__)
# this will log boto output to std out
logging.basicConfig(stream=sys.stdout, level=logging.INFO)

from dotenv import dotenv_values

config = dotenv_values(".env")

with open("userdata_base64.txt", "r") as fp:
    USERDATA_B64_STR = fp.read()

user = "root"
hosts = []

class CreateInstanceEC2(object):
    def __init__(self, ec2_client):
        self.ec2_client=ec2_client

    def get_vpc(self):
        vpc_id = ""
        response = self.ec2_client.describe_vpcs()
        for vpc in response["Vpcs"]:
            if vpc["Tags"][0]["Value"].__contains__("Default"):
                vpc_id = vpc["VpcId"]
                break

        response = self.ec2_client.describe_subnets(Filters=[{"Name":"vpc-id", "Values": [vpc_id]}])
        subnet_id = response["Subnets"][0]["SubnetId"]
        az = response["Subnets"][0]["AvailabilityZone"]
        return vpc_id, subnet_id, az

    def create_ec2_secgroup(self):
        sg_name = "awspy_security_group"
        print("Creating the Security Group {} : STARTED ".format(sg_name))
        try:
            vpc_id, subnet_id, az = self.get_vpc()
            response = self.ec2_client.create_security_group(
                GroupName=sg_name,
                Description="This SG is created using Python",
                VpcId=vpc_id
            )
            sg_id = response["GroupId"]
            sg_config = self.ec2_client.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort':22,
                        'IpRanges':[{'CidrIp':'0.0.0.0/0'}]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 2181,
                        'ToPort': 2181,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 0,
                        'ToPort': 65535,
                        'IpRanges': [{'CidrIp': '172.31.0.0/16'}]
                    }
                ]
            )
            print("Creating the Security Group {} : COMPLETED - Security Group ID: {} ".format(sg_name, sg_id))
            return sg_id, sg_name
        except Exception as e:
            if str(e).__contains__("already exists"):
                response = self.ec2_client.describe_security_groups(GroupNames=[sg_name])
                sg_id = response["SecurityGroups"][0]["GroupId"]
                print("Security Group {} already exists with Security Group ID: {} ".format(sg_name, sg_id))
                return sg_id, sg_name

    def create_ec2_launchtemplate(self):
        print("Creating the Launch Templates : STARTED ")
        template_name = 'awspy_launch_template'
        try:
            sg_id, sg_name = self.create_ec2_secgroup()
            response = self.ec2_client.create_launch_template(
                LaunchTemplateName=template_name,
                LaunchTemplateData={
                    'ImageId': 'ami-05e4673d4a28889fe',
                    'InstanceType' : "t2.micro",
                    'KeyName' : "vockey",#ec2-key
                    'Placement': {
                        'AvailabilityZone': 'us-east-1a',
                    },
                    'SecurityGroupIds': [securitygroup] if securitygroup else [sg_id],
                    'UserData': USERDATA_B64_STR,
                    'SecurityGroupIds': [sg_id]
                }
            )
            template_id = response['LaunchTemplate']['LaunchTemplateId']
            print("Creating the Launch Templates : COMPLETED : TemplateID:{}, TemplateName:{}".format(template_id, template_name ))
            return template_id, template_name
        except Exception as e:
            response = self.ec2_client.describe_launch_templates(
                LaunchTemplateNames=[
                    template_name,
                ]
            )
            template_id = response['LaunchTemplates'][0]['LaunchTemplateId']
            return template_id, template_name

    def create_ec2_group(self):
        print ("---- Started the creation of Auto Scaling Group using Launch Templates ----")
        launch_template_id, launch_template_name = self.create_ec2_launchtemplate()
        vpc_id, subnet_id, az = self.grep_vpc_subnet_id()
        client = boto3.client('autoscaling')
        self.autoscale_client = client
        minsize = 2
        maxsize = 5
        prefsize = 3
        with open("config.yaml") as f:
            try:
                config_ = yaml.load(f)
                maxsize = config_['zookeeper_max_nodes']
                minsize = config_['zookeeper_min_nodes']
                prefsize = config_['zookeeper_pref_nodes']

        response = client.create_auto_scaling_group(
            AutoScalingGroupName='awsk8s_autoscaling_group',
            LaunchTemplate={
                'LaunchTemplateId': launch_template_id,
            },
            MinSize=minsize,
            MaxSize=maxsize,
            DesiredCapacity=prefsize,
            AvailabilityZones=[
                az,
            ]
        )
        self.ec2_client.create_tags(
            Resources=[iid],
            Tags=[{'Key': 'Name', 'Value': name}]
        )
        if str(response["ResponseMetadata"]["HTTPStatusCode"]) == "200":
            groups = response.describe_auto_scaling_groups(AutoScalingGroupNames=['awsk8s_autoscaling_group',],).get("AutoScalingGroups")
            print(f"---- Creation of Auto Scaling Group using Launch Templates : COMPLETED ----")
            instances = (groups[0].get('Instances'))
            logger.info(instances) #maybe
            pubips = []
            privips = []
            ids = []
            for i in instances:
                i.wait_until_running('self',Filters=[{'Name':'state','Values':['available']}])
                pubip = self.ec2_client.Instance(i.get('InstanceId')).public_ip_address
                privip = self.ec2_client.Instance(i.get('InstanceId')).private_ip_address
                ids.append(i.get('InstanceId'))
                pubips.append(pubip)
                privips.append(privip)
                config_['hosts'][pubip] = privip
            hosts = [v for k, v in config_['hosts'].items()]
            with open("config.yaml", 'w') as f:
                try:
                    yaml.dump(loaded, f, default_flow_style=False)
                except yaml.YAMLError as exception:
                    print(exception)
            print(f"---- Added Auto Scaling Group to config.yaml for K8S : COMPLETED ; hosts={hosts}, IDs={ids}----")
        else:
            print("---- Creation of Auto Scaling Group using Launch Templates : FAILED ----")
        return True

@task
def create_instance_autoscaling_group(c, name='ccbd-video-processor', securitygroup=None):
    try:
        ec2_client = boto3.client('ec2', region_name='us-east-1', **config)
        ec2_instance = CreateInstanceEC2(ec2_client)
        ec2_instance.create_ec2_group() #ec2_instance.
    except ClientError as e:
        print(e)

@task
def create_instance(c, name='ccbd-video-processor', securitygroup=None):
    ec2 = boto3.resource('ec2', region_name='us-east-1', **config)
    instances = ec2.create_instances(
        # ImageId='ami-02e136e904f3da870', #(Amazon AMI)
        ImageId='ami-05e4673d4a28889fe',  # (Cloud9 Ubuntu - 2021-10-28T1333)
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.large',
        Placement={
            'AvailabilityZone': 'us-east-1a',
        },
        SecurityGroupIds=[securitygroup] if securitygroup else [],
        KeyName='vockey'
    )
    iid = instances[0].id
    # give the instance a tag name
    ec2.create_tags(
        Resources=[iid],
        Tags=[{'Key': 'Name', 'Value': name}]
    )
    logger.info(instances[0])


@task
def instancedetails(c, name):
    """
    Return an EC2 Instance
    :return:
    """
    ec2 = boto3.resource('ec2', region_name='us-east-1',
                         # pass content of config file as named args
                         **config
                         )
    instances = ec2.instances.filter(
        Filters=[{'Name': 'tag:Name', 'Values': [name]}])
    instances = list(instances)

    if len(instances) == 0:
        print('No instances - creating...')
        return create(c, name=name)
    else:
        for instance in instances:
            if instance.state['Name'] == "running":
                dns = instance.public_dns_name
                internal_ip = instance.private_ip_address
                public_ip = instance.public_ip_address
                logger.info(
                    f"Instance up and running at {dns} with internal ip {internal_ip}: {public_ip}: {internal_ip}")
            else:
                logger.warning(f"instance {instance.id} not running")

        ec2 = boto3.resource('ec2')

@task
def get_nodes(c):
    for host in hosts:
        con = Connection(f"{user}@{host}")
        con.sudo("kubectl get nodes")

@task
def terminate_instances(c, name):
    autoscaling = boto3.resource('autoscaling')
    groups = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=['awsk8s_autoscaling_group',],).get("AutoScalingGroups")
    instances = (groups[0].get('Instances'))
    instances.terminate()

@task
def waitfor_instances(c, name):
    autoscaling = boto3.resource('autoscaling')
    groups = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=['awsk8s_autoscaling_group',],).get("AutoScalingGroups")
    instances = (groups[0].get('Instances'))
    for instance in instances:
        instance.wait_until_running('self',Filters=[{'Name':'state','Values':['available']}])
    return True

@task
def getips_instances(c, _type):
    autoscaling = boto3.resource('autoscaling')
    groups = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=['awsk8s_autoscaling_group',],).get("AutoScalingGroups")
    with open('config.yaml') as f:
        config_ = yaml.load(f)
    hosts_ = [k for k, v in config_['hosts'].items()]
    if _type == "master":
        return hosts = [hosts_[0]]
    if _type == "slave":
        return hosts = hosts_[1:]
    if _type == "all":
        return hosts = hosts_

@task
def install_docker(c):
    print(f"Installing Docker on {c.host}")
    c.sudo("yum update && yum install -y docker")
    c.run("docker --version")
    c.sudo("systemctl enable docker.service")
    c.sudo("systemctl enable docker")
    c.sudo("usermod -aG docker ec2-user")
    c.sudo("yum install -y nc")

@task
def install_kubernetes(c):
    print(f"Installing Kubernetes on {c.host}")
    c.sudo("apt-get update")
    c.sudo("apt-get install -y apt-transport-https ca-certificates curl")
    c.sudo("curl -fsSLo /usr/share/keyrings/kubernetes-archive-keyring.gpg https://packages.cloud.google.com/apt/doc/apt-key.gpg")
    c.run('echo "deb [signed-by=/usr/share/keyrings/kubernetes-archive-keyring.gpg] https://apt.kubernetes.io/ kubernetes-xenial main" | sudo tee /etc/apt/sources.list.d/kubernetes.list')
    c.sudo("apt-get update")
    c.sudo("apt-get install -y kubelet kubeadm kubectl")
    c.sudo("apt-mark hold kubelet kubeadm kubectl")

@task
def prepare_instances(c):
    for host in hosts:
        con = Connection(f"{user}@{host}")
        install_docker(con)
        #disable_selinux_swap(conn)
        install_kubernetes(con)

@task
def prepare_master(c):
    for host in hosts:
        con = Connection(f"{user}@{host}")
        configure_k8s_master(con)
        get_join_token(con)

@task
def prepare_slave(c):
    with open("join_command.txt") as f:
        command = f.readline()
        for host in hosts:
            con = Connection(f"{user}@{host}")
            con.sudo(f"{command}")

@task
def configure_k8s_master(c):
    c.sudo("kubeadm init")
    c.sudo("mkdir -p $HOME/.kube")
    c.sudo("cp -i /etc/kubernetes/admin.conf $HOME/.kube/config")
    c.sudo("chown $(id -u):$(id -g) $HOME/.kube/config")
    c.sudo("kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml")

@task
def get_join_token(c):
    command_create_token = c.sudo("kubeadm token create --print-join-command")
    token = re.findall("^kubeadm.*$", str(command_create_token), re.MULTILINE)[0]

    with open("join_command.txt", "w") as f:
        with redirect_stdout(f):
            print(token)