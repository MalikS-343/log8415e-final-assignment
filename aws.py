import logging
logging.basicConfig(
    level=logging.INFO, 
    format="[%(levelname)s]:\t%(asctime)s %(message)s", 
    datefmt='%H:%M:%S'
)

import datetime
import time
import matplotlib.pyplot as plt
import boto3
from botocore.exceptions import ClientError
from constants import *

ec2 = boto3.client("ec2", region_name="us-east-1")
ec2_resource = boto3.resource("ec2", region_name="us-east-1")
cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")

def create_pem_key():
    try:
        response = ec2.create_key_pair(KeyName=KEY_NAME)
        logging.info(f"The pem key {KEY_FILENAME} has been created.")

        with open(KEY_FILENAME, 'w') as file:
            file.write(response['KeyMaterial'])
    except Exception as e:
        logging.warning(f'The key {KEY_FILENAME} already exists.')

def get_default_vpc_id() -> str:
    vpc_response = ec2.describe_vpcs(Filters = [
        {
            'Name': 'isDefault',
            'Values': ['true']
        }
    ])
    vpc_id = vpc_response['Vpcs'][0]['VpcId']
    logging.info(f'default VPC id: {vpc_id}')
    return vpc_id

def create_sg(vpc_id: str, group_name: str) -> str:
    security_group_id = ''
    try:
        response = ec2.create_security_group(
            GroupName=group_name,
            VpcId=vpc_id,
            Description=group_name
        )
        security_group_id = response['GroupId']

        response = ec2.describe_security_groups(GroupIds = [security_group_id])

        egress_rules = response['SecurityGroups'][0].get('IpPermissionsEgress', [])
        for rule in egress_rules:
            ec2.revoke_security_group_egress(
                GroupId=security_group_id,
                IpPermissions=[rule]
            )
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidGroup.Duplicate':
            logging.warning(f'The security group {group_name} already exists.')
            response = ec2.describe_security_groups(
                Filters=[
                    {
                        'Name': 'group-name',
                        'Values': [group_name]
                    }
                ]
            )
            security_group_id = response['SecurityGroups'][0]['GroupId']
        else:
            raise

    return security_group_id

def create_g_sc(vpc_id: str):
    gatekeeper_security_group_id = create_sg(vpc_id, 'gatekeeper security group')

    try:
        ec2.authorize_security_group_ingress(
            GroupId=gatekeeper_security_group_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': SSH_PORT,
                    'ToPort': SSH_PORT,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                },
                {
                    'IpProtocol': 'tcp',
                    'FromPort': HTTP_PORT,
                    'ToPort': HTTP_PORT,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }
            ]
        )

        ec2.authorize_security_group_egress(
            GroupId=gatekeeper_security_group_id,
            IpPermissions=[
                {
                    'IpProtocol': '-1',  # Allow all traffic
                    'FromPort': 0,
                    'ToPort': 65535,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]  # Allow all outbound
                }
            ]
        )
    except ClientError as e:
        if (e.response['Error']['Code'] == 'InvalidPermission.Duplicate'):
            logging.warning(f'The gatekeeper security group has already the necessary permissions.')
        else:
            raise

    return gatekeeper_security_group_id

def authorize_traffic_between_sgs(sg1_id: str, sg2_id: str, port: int, protocol:str='tcp'):
    try:
        ec2.authorize_security_group_ingress(
            GroupId=sg1_id,
            IpPermissions=[
                {
                    'IpProtocol': protocol,
                    'FromPort': port,
                    'ToPort': port,
                    'UserIdGroupPairs': [
                        {
                            'GroupId': sg2_id
                        }
                    ]
                }
            ]
        )
        ec2.authorize_security_group_ingress(
            GroupId=sg2_id,
            IpPermissions=[
                {
                    'IpProtocol': protocol,
                    'FromPort': port,
                    'ToPort': port,
                    'UserIdGroupPairs': [
                        {
                            'GroupId': sg1_id
                        }
                    ]
                }
            ]
        )
        ec2.authorize_security_group_egress(
            GroupId=sg2_id,
            IpPermissions=[
                {
                    'IpProtocol': protocol,
                    'FromPort': port,
                    'ToPort': port,
                    'UserIdGroupPairs': [
                        {
                            'GroupId': sg1_id
                        }
                    ]
                }
            ]
        )
        ec2.authorize_security_group_egress(
            GroupId=sg1_id,
            IpPermissions=[
                {
                    'IpProtocol': protocol,
                    'FromPort': port,
                    'ToPort': port,
                    'UserIdGroupPairs': [
                        {
                            'GroupId': sg2_id
                        }
                    ]
                }
            ]
        )
    except ClientError as e:
        if (e.response['Error']['Code'] == 'InvalidPermission.Duplicate'):
            logging.warning(f'The traffic between the security groups {sg1_id} and {sg2_id} on the port {port} is already authorized.')
        else:
            raise

def create_instances(instance_type: str, number_of_instances: int, security_group_id: str, name: str = None):
    logging.info(f"Creating {number_of_instances} {instance_type} instance(s)")
    try:
        instances = ...
        if name is None:
            instances = ec2.run_instances(
                ImageId="ami-0e86e20dae9224db8",  # Ubuntu image
                MinCount=number_of_instances,
                MaxCount=number_of_instances,
                KeyName=KEY_NAME,
                InstanceType=instance_type,
                SecurityGroupIds=[security_group_id]
            )
        else:
            instances = ec2.run_instances(
                ImageId="ami-0e86e20dae9224db8",  # Ubuntu image
                MinCount=number_of_instances,
                MaxCount=number_of_instances,
                KeyName=KEY_NAME,
                InstanceType=instance_type,
                SecurityGroupIds=[security_group_id],
                TagSpecifications=[
                    {
                        'ResourceType': 'instance',
                        'Tags': [
                            {
                                'Key': 'Name',
                                'Value': name
                            }
                        ]
                    }
                ]
            )
        logging.info(f"Created {number_of_instances} {instance_type} instance(s)")
        return get_instance_ids(instances)
    except Exception as e:
        logging.error(e)

def wait_for_instances(instance_ids):
    for instance_id in instance_ids:
        instance_ressource = ec2_resource.Instance(instance_id)
        logging.info(f"Waiting until running: {instance_id}")
        instance_ressource.wait_until_running()
    sleep_time = 10
    logging.info(f"Waiting {sleep_time}s")
    time.sleep(sleep_time)

def get_public_dns_names(instance_ids):
    new_instance_desc = ec2.describe_instances(InstanceIds = instance_ids)
    instances = new_instance_desc['Reservations'][0]['Instances']
    public_dns_names = [instance['PublicDnsName'] for instance in instances]
    return public_dns_names

def get_private_dns_names(instance_ids):
    new_instance_desc = ec2.describe_instances(InstanceIds = instance_ids)
    instances = new_instance_desc['Reservations'][0]['Instances']
    private_dns_names = [instance['PrivateDnsName'] for instance in instances]
    return private_dns_names

def get_instance_ids(instance_response):
    instances = instance_response['Instances']
    instance_ids = [instance['InstanceId'] for instance in instances]
    return instance_ids

def get_private_ips(instance_ids):
    new_instance_desc = ec2.describe_instances(InstanceIds = instance_ids)
    instances = new_instance_desc['Reservations'][0]['Instances']
    private_ip_addresses = [instance['PrivateIpAddress'] for instance in instances]
    return private_ip_addresses


def get_cloudwatch_infos(end_time, fig_name, names: list[str], ids: list[str]):
    metric_data_queries = [
                {
                    'Id': 'i' + ids[i][2:],
                    'MetricStat': {
                        'Metric': {
                            'Namespace': 'AWS/EC2',
                            'MetricName': 'CPUUtilization',
                            'Dimensions': [
                                {
                                    'Name': 'InstanceId',
                                    'Value': ids[i],
                                }
                            ]
                        },
                        'Period': 300,
                        'Stat': 'Maximum',
                        'Unit': 'Percent'
                    },
                    'Label': names[i]
                }
            for i in range(len(ids))]
    
    response = cloudwatch.get_metric_data(
        MetricDataQueries = metric_data_queries,
        StartTime = end_time - datetime.timedelta(seconds=300),
        EndTime = end_time
    )

    master_value = ...
    worker1_value = ...
    worker2_value = ...
    for data_results in response['MetricDataResults']:
        if data_results['Label'] == names[0]:
            master_value = data_results['Values'][0]
        elif data_results['Label'] == names[1]:
            worker1_value = data_results['Values'][0]
        elif data_results['Label'] == names[2]:
            worker2_value = data_results['Values'][0]

    x = names
    y = [master_value, worker1_value, worker2_value]

    plt.figure(figsize=(10, 6))  # Width, Height in inches
    plt.bar(x, y, width=0.25)
    plt.xlabel('EC2 instance')
    plt.ylabel('Maximum CPU Utilization (%)')
    plt.title(f'Maximum CPU Utilization of each cluster during {fig_name} benchmarking')
    plt.savefig(fig_name)
    plt.clf()