import sys
import time

import yaml
import boto3
import base64
import logging
from fabric import task, Connection
from botocore.exceptions import ClientError
from contextlib import redirect_stdout
import re


#with open("userdata_base64.txt", "r") as fp:
#    USERDATA_B64_STR = fp.read()

valid_instance_group_types = {"kubernetes-controlplane", "kubernetes-worker"}
ec2_secgroup_ip_permissions = [
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

    def create_ec2_secgroup(self, logger, ip_permissions=[]):
        if len(ip_permissions) == 0:
            raise ValueError(f"Error: 'ip_permissions' must be supplied")
        if all(perm["IpProtocol"] is not None and perm["FromPort"] is not None and perm["ToPort"] is not None and perm["IpRanges"] is not None for perm in ip_permissions):
            raise ValueError("Error: each ip_permission must be in the form { \
                        'IpProtocol': 'tcp' \
                        'FromPort': 22, \
                        'ToPort': 22, \
                        'IpRanges':[{'CidrIp':'0.0.0.0/0'}]}")
        sg_name = "awspy_security_group"
        logger.info(f"Creating the Security Group {sg_name} : STARTED ")
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
                IpPermissions=ip_permissions
            )
            logger.info("Creating the Security Group {sg_name} : COMPLETED - Security Group ID: {sg_id}")
            return sg_id, sg_name
        except Exception as e:
            if str(e).__contains__("already exists"):
                response = self.ec2_client.describe_security_groups(GroupNames=[sg_name])
                sg_id = response["SecurityGroups"][0]["GroupId"]
                logger.info("Security Group {sg_name} already exists with Security Group ID: {sg_id}")
                return sg_id, sg_name

    def create_ec2_launchtemplate(self, logger, instance_name, template_name="ec2_launch_template", image_id="ami-05e4673d4a28889fe", az_region="us-east-1a", aws_instance_type='t2.micro', securitygroup=None):
        logger.info("Creating the Launch Templates : STARTED ")
        try:
            sg_id, sg_name = self.create_ec2_secgroup()
            response = self.ec2_client.create_launch_template(
                LaunchTemplateName=template_name,
                LaunchTemplateData={
                    'ImageId': image_id,
                    'InstanceType' : aws_instance_type,
                    'KeyName' : 'vockey',#ec2-key
                    'Placement': {
                        'AvailabilityZone': az_region,
                    },
                    'SecurityGroupIds': [securitygroup] if securitygroup is not None else [sg_id],
                    #'UserData': USERDATA_B64_STR
                }
            )
            template_id = response['LaunchTemplate']['LaunchTemplateId']
            logger.info(f"Creating the Launch Templates : COMPLETED : TemplateID:{template_id}, TemplateName:{template_name}")
            return template_id, template_name
        except Exception as e:
            response = self.ec2_client.describe_launch_templates(
                LaunchTemplateNames=[
                    template_name,
                ]
            )
            template_id = response['LaunchTemplates'][0]['LaunchTemplateId']
            return template_id, template_name

    def create_ec2_group(self, logger, instance_name, instance_type="kubernetes-worker", group_name=None, template_name="ec2_launch_template", image_id="ami-05e4673d4a28889fe", az_region="us-east-1a", aws_instance_type='t2.micro', securitygroup=None):
        logger.info("---- Started the creation of Auto Scaling Group using Launch Templates ----")
        launch_template_id, launch_template_name = self.create_ec2_launchtemplate(logger, instance_name, template_name=template_name, image_id=image_id, az_region=az_region, aws_instance_type=aws_instance_type, securitygroup=securitygroup)
        vpc_id, subnet_id, az = self.get_vpc()
        client = boto3.client('autoscaling')
        self.autoscale_client = client
        minsize = 2
        maxsize = 5
        prefsize = 3
        if instance_type not in valid_instance_group_types:
            raise ValueError(f"Error: type '{instance_type}' is not a valid instance group type: {valid_instance_group_types}")
        with open("config.yaml") as f:
            try:
                config_ = yaml.load(f, Loader=yaml.SafeLoader)
                maxsize = config_[f'{instance_type}_max_nodes']
                minsize = config_[f'{instance_type}_min_nodes']
                prefsize = config_[f'{instance_type}_pref_nodes']
            except:
                pass
                
        response = client.create_auto_scaling_group(
            AutoScalingGroupName=group_name if group_name is not None else f'asg_{instance_type}',
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
            Resources=[image_id],
            Tags=[{'Key': 'Name', 'Value': template_name}, {'Key': 'Instance Type', 'Value': instance_type}]
        )
        if str(response["ResponseMetadata"]["HTTPStatusCode"]) == "200":
            groups = response.describe_auto_scaling_groups(AutoScalingGroupNames=[group_name,],).get("AutoScalingGroups")
            logger.info(f"---- Creation of Auto Scaling Group using Launch Templates : COMPLETED ----")
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
                with open("config.yaml") as f:
                    config_['hosts'][pubip] = privip
            hosts = [v for k, v in config_['hosts'].items()]
            newhosts = privips
            with open("config.yaml", 'w') as f:
                try:
                    yaml.dump(config_, f, default_flow_style=False)
                except yaml.YAMLError as exception:
                    logger.warning(exception)
                    raise ValueError("Error: could not open 'config.yaml'")
            logger.info(f"---- Added Auto Scaling Group to config.yaml for K8S : COMPLETED ; hosts={hosts}, IDs={ids}----")
        else:
            logger.info("---- Creation of Auto Scaling Group using Launch Templates : FAILED ----")
        return hosts, ids, pubips, privips

# ImageId='ami-02e136e904f3da870', #(Amazon AMI)
# ImageId='ami-05e4673d4a28889fe',  # (Cloud9 Ubuntu - 2021-10-28T1333)
@task
def create_instance_autoscaling_group(c, config, logger, instance_name="barry", instance_type="kubernetes-worker", group_name=None, template_name="ec2_launch_template", image_id="ami-05e4673d4a28889fe", az_region="us-east-1a", securitygroup=None):
    """
    Creates an AWS ASG of the specified instance_type
    """
    try:
        ec2_client = boto3.client(instance_type, region_name=az_region, **config)
        ec2_instance = CreateInstanceEC2(ec2_client, logger)
        updated_hosts, ids, pubips, privips = ec2_instance.create_ec2_group(logger=logger, instance_name=instance_name, instance_type=instance_type, group_name=group_name, template_name=template_name, image_id=image_id, az_region=az_region, securitygroup=securitygroup) #ec2_instance.
    except ClientError as e:
        logger.warning(e)

@task
def create_instance(c, config, logger, instance_type="kubernetes-worker", instance_name="new_ec2_instance", image_id="ami-05e4673d4a28889fe", az_region="us-east-1a", aws_instance_type='t2.large', securitygroup=None):
    """
    Creates a singular EC2 instance
    """
    ec2 = boto3.resource('ec2', region_name=az_region, **config)
    instances = ec2.create_instances(
        ImageId=image_id,
        MinCount=1,
        MaxCount=1,
        InstanceType=aws_instance_type,
        Placement={
            'AvailabilityZone': az_region,
        },
        SecurityGroupIds=[securitygroup] if securitygroup else [],
        KeyName='vockey'
    )
    iid = instances[0].id
    # give the instance a tag name
    ec2.create_tags(
        Resources=[iid],
        Tags=[{'Key': 'Name', 'Value': instance_name}, {'Key': 'Instance Type', 'Value': instance_type}]
    )
    logger.info(instances[0])
    return instances[0]

@task
def instancedetails(c, config, logger, instance_name, az_region="us-east-1a"):
    """
    Returns the specific EC2 Instance(s) that are running
    """
    ec2 = boto3.resource('ec2', region_name=az_region, **config)
    instances = ec2.instances.filter(
        Filters=[{'Name': 'tag:Name', 'Values': [instance_name]}])
    instances = list(instances)

    if len(instances) == 0:
        logger.warning(f"   Error: No instances with 'Name' {instance_name} - creating...")
        return create_instance(c, instance_name=instance_name)
    else:
        running_instances = []
        for instance in instances:
            if instance.state['Name'] == "running":
                dns = instance.public_dns_name
                internal_ip = instance.private_ip_address
                public_ip = instance.public_ip_address
                logger.info(
                    f"Instance up and running at {dns} with internal ip {internal_ip}: {public_ip}: {internal_ip}")
                running_instances.append(instance)
            else:
                logger.warning(f"   Instance with id={instance.id} is not running")

        ec2 = boto3.resource('ec2')
        return instances

@task
def terminate_instances(c, group_name):
    """
    Terminates all instances in ASG with group_name
    """
    autoscaling = boto3.resource('autoscaling')
    groups = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[group_name,],).get("AutoScalingGroups")
    instances = (groups[0].get('Instances'))
    instances.terminate()

@task
def waitfor_instances(c, group_name):
    """
    Waits for all instances in the ASG with group_name
    """
    autoscaling = boto3.resource('autoscaling')
    groups = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[group_name,],).get("AutoScalingGroups")
    instances = (groups[0].get('Instances'))
    for instance in instances:
        instance.wait_until_running('self',Filters=[{'Name':'state','Values':['available']}])
    return True

@task
def getips_instances(c, config, group_name):
    """
    Returns (public_ips[], private_ips[]) for all instances in the ASG with group_name
    """
    autoscaling = boto3.resource('autoscaling')
    groups = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[group_name,],).get("AutoScalingGroups")
    pubips = [k for k, v in config['hosts'].items()]
    privips = [v for k, v in config['hosts'].items()]
    return pubips, privips

@task
def get_nodes(c, user, hosts):
    for host in hosts:
        con = Connection(f"{user}@{host}")
        con.sudo("kubectl get nodes")

@task
def install_docker(c, logger):
    logger.info(f"Installing Docker on {c.host}")
    c.sudo("yum update && yum install -y docker")
    c.run("docker --version")
    c.sudo("systemctl enable docker.service")
    c.sudo("systemctl enable docker")
    c.sudo("usermod -aG docker ec2-user")
    c.sudo("yum install -y nc")

@task
def install_kubernetes(c, logger):
    logger.info(f"Installing Kubernetes on {c.host}")
    c.sudo("apt-get update")
    c.sudo("apt-get install -y apt-transport-https ca-certificates curl")
    c.sudo("curl -fsSLo /usr/share/keyrings/kubernetes-archive-keyring.gpg https://packages.cloud.google.com/apt/doc/apt-key.gpg")
    c.run('echo "deb [signed-by=/usr/share/keyrings/kubernetes-archive-keyring.gpg] https://apt.kubernetes.io/ kubernetes-xenial main" | sudo tee /etc/apt/sources.list.d/kubernetes.list')
    c.sudo("apt-get update")
    c.sudo("apt-get install -y kubelet kubeadm kubectl")
    c.sudo("apt-mark hold kubelet kubeadm kubectl")

@task
def configure_k8s_master(c):
    c.sudo("kubeadm init")
    c.sudo("mkdir -p $HOME/.kube")
    c.sudo("cp -i /etc/kubernetes/admin.conf $HOME/.kube/config")
    c.sudo("chown $(id -u):$(id -g) $HOME/.kube/config")
    c.sudo("kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml")

@task
def prepare_instances(c, user, host):
    con = Connection(f"{user}@{host}")
    install_docker(con)
    #disable_selinux_swap(conn)
    install_kubernetes(con)

@task
def prepare_masters(c, user, host):
    configure_k8s_master(c)
    get_join_token(c)

@task
def prepare_slaves(c, user, host):
    with open("join_command.txt") as f:
        command = f.readline()
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
def get_join_token(c, logger):
    command_create_token = c.sudo("kubeadm token create --print-join-command")
    token = re.findall("^kubeadm.*$", str(command_create_token), re.MULTILINE)[0]

    with open("join_command.txt", "w") as f:
        with redirect_stdout(f):
            logger.info(token)