import sys
import time
from tracemalloc import take_snapshot

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

valid_instance_group_types = {"ec2"}
valid_instance_group_nodetypes = {"kubernetes_controlplane", "kubernetes_worker"}
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
    def __init__(self, ec2_client, logger, config, context):
        self.ec2_client = ec2_client
        self.logger = logger
        self.config = config
        self.context = context

    def get_vpc(self):
        vpc_ids = []
        response = self.ec2_client.describe_vpcs()
        for vpc in response["Vpcs"]:
            #self.logger.info(vpc)
            #if vpc["Tags"][0]["Value"].__contains__("Default"):
            #    vpc_id = vpc["VpcId"]
            vpc_id = vpc["VpcId"]
            vpc_ids.append(vpc_id)

        response = self.ec2_client.describe_subnets(Filters=[{"Name": "vpc-id", "Values": vpc_ids}])
        subnet_id = response["Subnets"][0]["SubnetId"]
        az = response["Subnets"][0]["AvailabilityZone"]
        return vpc_ids, subnet_id, az

    def create_ec2_secgroup(self, logger, ip_permissions=[]):
        #EC2SecurityGroup:
        #   Type: AWS::EC2::SecurityGroup
        #   Properties:
        #   GroupDescription: Security Group for EC2 instances.
        #   #Other properties including SecurityGroupIngress, SecurityGroupEgress, VpcId
        
        if len(ip_permissions) == 0:
            raise ValueError(f"Error: 'ip_permissions' must be supplied")
        if not all(perm["IpProtocol"] is not None and perm["FromPort"] is not None and perm["ToPort"] is not None and perm["IpRanges"] is not None for perm in ip_permissions):
            raise ValueError("Error: each ip_permission must be in the form { \
                        'IpProtocol': 'tcp' \
                        'FromPort': 22, \
                        'ToPort': 22, \
                        'IpRanges':[{'CidrIp':'0.0.0.0/0'}]}")
        sg_name = "awspy_security_group"
        logger.info(f"Creating the Security Group {sg_name} : STARTED ")
        try:
            keypair_name = "vockey"
            response = self.ec2_client.describe_key_pairs()
            #logger.info(response)
            if not any(r['KeyName'] == keypair_name for r in response['KeyPairs']):
                response = self.ec2_client.create_key_pair(KeyName=keypair_name)
            vpc_id, subnet_id, az = self.get_vpc()
            response = self.ec2_client.create_security_group(
                GroupName=sg_name,
                Description="This SG is created using Python",
                VpcId=vpc_id
            )
            response = self.ec2_client.describe_security_groups(GroupNames=[sg_name])
            sg_id = response["SecurityGroups"][0]["GroupId"]
            sg_config = self.ec2_client.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=ip_permissions
            )
            logger.info(f"Creating the Security Group {sg_name} : COMPLETED - Security Group ID: {sg_id}")
            return sg_id, sg_name, vpc_id, subnet_id, az
        except Exception as e:
            if str(e).__contains__("already exists"):
                response = self.ec2_client.describe_security_groups(GroupNames=[sg_name])
                sg_id = response["SecurityGroups"][0]["GroupId"]
                logger.warning(f"   Security Group {sg_name} already exists with Security Group ID: {sg_id}")
            raise ValueError(e)

    def create_ec2_launchtemplate(self, logger, ip_permissions, instance_name, template_name="ec2_launch_template", image_id="ami-05e4673d4a28889fe", az_region="us-east-1", aws_instance_type='t2.micro', securitygroup=None):
        #DemoLaunchTemplate:
        #    Type: AWS::EC2::LaunchTemplate
        #    Properties:
        #    LaunchTemplateName: demo-launch-template
        #    LaunchTemplateData:
        #        BlockDeviceMappings:
        #        - Ebs:
        #            VolumeSize: 8
        #            VolumeType: gp2
        #            DeleteOnTermination: true
        #            Encrypted: true
        #            DeviceName: /dev/xvdh
        #        ImageId: ami-098f16afa9edf40be
        #        InstanceType: t2.micro
        #        SecurityGroupIds:
        #        - !GetAtt EC2SecurityGroup.GroupId
        
        logger.info("Creating the Launch Templates : STARTED ")
        try:
            sg_id, sg_name, vpc_id, subnet_id, az = self.create_ec2_secgroup(logger, ip_permissions)
            keypair_name = "vockey"
            response = self.ec2_client.describe_key_pairs()
            #logger.info(response)
            if not any(r['KeyName'] == keypair_name for r in response['KeyPairs']):
                response = self.ec2_client.create_key_pair(KeyName=keypair_name)
            """
            aws ec2 create-key-pair \
                --key-name {keypair_name} \
                --key-type rsa \
                --key-format pem \
                --query 'KeyMaterial' \
                --output text > {keypair_name}.pem
                
            aws ec2 import-key-pair
                --key-name {keypair_name}
                --public-key-material {keypair_name}.pem
            """
            response = self.ec2_client.create_launch_template(
                LaunchTemplateName=template_name,
                LaunchTemplateData={
                    'ImageId': image_id,
                    'InstanceType' : aws_instance_type,
                    'KeyName' : keypair_name,#ec2-key
                    'Placement': {
                        'AvailabilityZone': az_region,
                    },
                    'SecurityGroupIds': [securitygroup] if securitygroup is not None else [sg_id],
                    #'UserData': USERDATA_B64_STR
                }
            )
            template_id = response['LaunchTemplate']['LaunchTemplateId']
            logger.info(f"Creating the Launch Templates : COMPLETED : TemplateID:{template_id}, TemplateName:{template_name}")
            return template_id, template_name, vpc_id, subnet_id, az
        except Exception as e:
            response = self.ec2_client.describe_launch_templates(
                LaunchTemplateNames=[
                    template_name,
                ]
            )
            template_id = response['LaunchTemplates'][0]['LaunchTemplateId']
            keypair_name = "vockey"
            response = self.ec2_client.describe_key_pairs()
            #logger.info(response)
            if not any(r['KeyName'] == keypair_name for r in response['KeyPairs']):
                response = self.ec2_client.create_key_pair(KeyName=keypair_name)
            vpc_id, subnet_id, az = self.get_vpc()
            return template_id, template_name, vpc_id, subnet_id, az

    def create_ec2_group(self, config_env, ip_permissions, logger, instance_name, instance_nodetype="kubernetes_worker", instance_type="ec2", group_name=None, template_name="ec2_launch_template", image_id="ami-05e4673d4a28889fe", az_region="us-east-1", aws_instance_type='t2.micro', securitygroup=None, minsize=2, maxsize=4, prefsize=3):
        logger.info("---- Started the creation of Auto Scaling Group using Launch Templates ----")
        launch_template_id, launch_template_name, vpc_id, subnet_id, az = self.create_ec2_launchtemplate(logger, ip_permissions, instance_name, template_name=template_name, image_id=image_id, az_region=az_region, aws_instance_type=aws_instance_type, securitygroup=securitygroup)
        client = boto3.client('autoscaling', region_name=az_region, **config_env)
        self.autoscale_client = client
        if instance_type not in valid_instance_group_types:
            raise ValueError(f"Error: type '{instance_type}' is not a valid instance group type: {valid_instance_group_types}")
        if instance_nodetype not in valid_instance_group_nodetypes:
            raise ValueError(f"Error: type '{instance_nodetype}' is not a valid instance group type: {valid_instance_group_nodetypes}")
        with open("config.yml") as f:
            try:
                config_ = yaml.load(f, Loader=yaml.SafeLoader)
                maxsize = config_[f'{instance_nodetype}_max_nodes']
                minsize = config_[f'{instance_nodetype}_min_nodes']
                prefsize = config_[f'{instance_nodetype}_pref_nodes']
            except:
                pass
        #DemoAutoScalingGroup:
        #    Type: AWS::AutoScaling::AutoScalingGroup
        #    Properties:
        #    AutoScalingGroupName: demo-auto-scaling-group
        #    MinSize: "2"
        #    MaxSize: "4"
        #    DesiredCapacity: "2"
        #    HealthCheckGracePeriod: 300
        #    LaunchTemplate:
        #        LaunchTemplateId: !Ref DemoLaunchTemplate
        #        Version: !GetAtt DemoLaunchTemplate.LatestVersionNumber
        #    VPCZoneIdentifier:
        #        - subnet-0123
        #        - subnet-0456 
        groups = client.describe_auto_scaling_groups(AutoScalingGroupNames=[group_name,],).get("AutoScalingGroups")
        if any(g['AutoScalingGroupName'] == group_name for g in groups):
            logger.warning(f"Autoscaling Group with name {group_name} already exists")
            response = None
        else:
            response = client.create_auto_scaling_group(
                AutoScalingGroupName=group_name if group_name is not None else f'asg_{instance_nodetype}',
                MinSize=minsize,
                MaxSize=maxsize,
                DesiredCapacity=prefsize,
                HealthCheckGracePeriod=300,
                LaunchTemplate={
                    'LaunchTemplateId': launch_template_id
                },
                VPCZoneIdentifier=
                    subnet_id, #vpc_id
                AvailabilityZones=[
                    az_region,#az
                ]
            )
        self.ec2_client.create_tags(
            Resources=[image_id],
            Tags=[{'Key': 'Name', 'Value': template_name}, {'Key': 'Instance Type', 'Value': instance_nodetype}]
        )
        logger.info("Created autoscaling group successfully.")
        if response is None or str(response["ResponseMetadata"]["HTTPStatusCode"]) == "200":
            logger.info(f"---- Creation of Auto Scaling Group using Launch Templates : COMPLETED ----")
            instances = (groups[0].get('Instances'))
            pubips = []
            privips = []
            ids = []
            hs = []
            for ind, i in enumerate(instances):
                pubip, privip = get_ip_from_instance_id(self.context, i.get('InstanceId'), az_region, config_env)
                logger.info(f"IPs of instance {ind}: PUB: {pubip}, PRIV: {privip}")
                ids.append(i.get('InstanceId'))
                pubips.append(pubip)
                privips.append(privip)
                config_['hosts'][pubip] = privip
            hosts = config_['hosts'].items()
            logger.info(f"Created {len(instances)} Instances; {hosts}") #maybe
            with open("config.yml", 'w') as f:
                try:
                    yaml.dump(config_, f, default_flow_style=False)
                except yaml.YAMLError as exception:
                    logger.warning(exception)
                    raise ValueError("Error: could not open 'config.yml'")
            logger.info(f"---- Added Auto Scaling Group to config.yml for K8S : COMPLETED ----")
            return hosts, ids, pubips, privips
        else:
            logger.info("---- Creation of Auto Scaling Group using Launch Templates : FAILED ----")
            return None, None, None, None

# ImageId='ami-02e136e904f3da870', #(Amazon AMI)
# ImageId='ami-05e4673d4a28889fe',  # (Cloud9 Ubuntu - 2021-10-28T1333)
@task
def create_instance_autoscaling_group(c, config, config_env, logger, instance_name="barry", instance_nodetype="kubernetes_worker", instance_type="ec2", group_name=None, template_name="ec2_launch_template", image_id="ami-05e4673d4a28889fe", az_region="us-east-1", securitygroup=None):
    """
    Creates an AWS ASG of the specified instance_type
    """
    try:
        ec2_client = boto3.client(instance_type, region_name=az_region, **config_env)
        ec2_instance = CreateInstanceEC2(ec2_client, logger, config, c)
        updated_hosts, ids, pubips, privips = ec2_instance.create_ec2_group(config_env=config_env, ip_permissions=ec2_secgroup_ip_permissions, logger=logger, instance_nodetype=instance_nodetype, instance_type=instance_type, instance_name=instance_name, group_name=group_name, template_name=template_name, image_id=image_id, az_region=az_region, securitygroup=securitygroup) #ec2_instance.
        return updated_hosts, ids, pubips, privips
    except ClientError as e:
        logger.warning(e)
        return None, None, None, None

@task
def create_instance(c, config, config_env, logger, instance_type="kubernetes_worker", instance_name="new_ec2_instance", image_id="ami-05e4673d4a28889fe", az_region="us-east-1a", aws_instance_type='t2.large', securitygroup=None):
    """
    Creates a singular EC2 instance
    """
    ec2 = boto3.resource('ec2', region_name=az_region, **config_env)
    keypair_name = "vockey"
    response = ec2.create_key_pair(KeyName=keypair_name)
    response = ec2.describe_key_pairs()
    logger.info(response)
    instances = ec2.create_instances(
        ImageId=image_id,
        MinCount=1,
        MaxCount=1,
        InstanceType=aws_instance_type,
        Placement={
            'AvailabilityZone': az_region,
        },
        SecurityGroupIds=[securitygroup] if securitygroup else [],
        KeyName=keypair_name
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
def get_ip_from_instance_id(c, instance_id, az_region, config_env):
    ec2 = boto3.client('ec2', region_name=az_region, **config_env)
    pubip = ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]['PrivateDnsName']
    privip = ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]['PublicDnsName']
    return pubip, privip
                

@task
def instancedetails(c, config, config_env, logger, instance_name, az_region="us-east-1"):
    """
    Returns the specific EC2 Instance(s) that are running
    """
    ec2 = boto3.resource('ec2', region_name=az_region, **config_env)
    instances = ec2.instances.filter(
        Filters=[{'Name': 'tag:Name', 'Values': [instance_name]}])
    instances = list(instances)

    if len(instances) == 0:
        logger.warning(f"   Error: No instances with 'Name' {instance_name} - creating...")
        return create_instance(c, config=config, config_env=config_env, instance_name=instance_name)
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

        ec2 = boto3.resource('ec2', region_name=az_region, **config_env)
        return instances

@task
def terminate_instances(c, group_name, az_region, config_env):
    """
    Terminates all instances in ASG with group_name
    """
    ec2 = boto3.client('ec2', region_name=az_region, **config_env)
    groups = ec2.describe_auto_scaling_groups(AutoScalingGroupNames=[group_name,],).get("AutoScalingGroups")
    instances = (groups[0].get('Instances'))
    response = ec2.stop_instances(InstanceIds=instances, DryRun=False)

@task
def waitfor_instances(c, group_name, az_region, config_env):
    """
    Waits for all instances in the ASG with group_name  
    #TODO NOT WORKING
    """
    autoscaling = boto3.client('autoscaling', region_name=az_region, **config_env)
    groups = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[group_name,],).get("AutoScalingGroups")
    instances = (groups[0].get('Instances'))
    return instances

@task
def getips_instances(c, config, group_name, az_region, config_env):
    """
    Returns (public_ips[], private_ips[]) for all instances in the ASG with group_name
    """
    autoscaling = boto3.client('autoscaling', region_name=az_region, **config_env)
    groups = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=[group_name,],).get("AutoScalingGroups")
    pubips = [k for (k, v) in config['hosts']]
    privips = [v for (k, v) in config['hosts']]
    return pubips, privips

@task
def get_nodes(c, con):
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
def prepare_instances(c):
    install_docker(c)
    #disable_selinux_swap(conn)
    install_kubernetes(c)

@task
def prepare_master(c, logger):
    install_kubernetes(c, logger)
    configure_k8s_master(c)
    token = get_join_token(c)
    return token

@task
def prepare_slaves(c):
    with open("join_command.txt") as f:
        command = f.readline()
        c.sudo(f"{command}")

@task
def get_join_token(c, logger):
    command_create_token = c.sudo("kubeadm token create --print-join-command")
    token = re.findall("^kubeadm.*$", str(command_create_token), re.MULTILINE)[0]

    with open("join_command.txt", "w") as f:
        with redirect_stdout(f):
            logger.info(token)
    return token