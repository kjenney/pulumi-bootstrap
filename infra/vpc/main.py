import pulumi
import pulumi_aws as aws
import sys

sys.path.append("../..//shared")
from bootstrap import *

def pulumi_program():
    config = pulumi.Config()
    environment = config.require('environment')
    aws_region = config.require('aws_region')
    data = get_config(environment)
    vpc_cidr = data['vpc']['cidr']
    if '/16' in vpc_cidr:
        vpc_name = f"main-{environment}"
    else:
        raise ValueError('The VPC must use /16 CIDR.')
    tags = {
        "Name": vpc_name,
        "Environment": environment,
        "Managed By": "Pulumi",
    }
    vpc = aws.ec2.Vpc(vpc_name, 
                      cidr_block=vpc_cidr, 
                      tags=tags,
                      enable_dns_hostnames=True,
    )
    number_of_subnets = len(data['vpc']['subnets'].keys()) + 1
    internet_gateway = aws.ec2.InternetGateway("gw",
        vpc_id=vpc.id,
        tags={
            "Name": vpc_name,
            "Environment": environment,
            "Managed By": "Pulumi",
        })
    public_route = aws.ec2.RouteTable("public",
        vpc_id=vpc.id,
        routes=[
            aws.ec2.RouteTableRouteArgs(
                cidr_block="0.0.0.0/0",
                gateway_id=internet_gateway.id,
            )
        ],
        tags={
            "Name": f"{vpc_name}-public",
            "Environment": environment,
            "Managed By": "Pulumi",
        }
    )
    for x in range(1, number_of_subnets):
        subnet_id = f"subnet{x}"
        subnet_config = data['vpc']['subnets'][subnet_id]
        subnet = aws.ec2.Subnet(subnet_id,
            vpc_id=vpc.id,
            availability_zone=f"{aws_region}{subnet_config['az']}",
            cidr_block=subnet_config['cidr'],
            tags={
                "Name": f"{subnet_id}-{vpc_name}",
                "Environment": environment,
                "Type": subnet_config['type'],
                "Managed By": "Pulumi",
        })
        pulumi.export(f"{subnet_id}_cidr", subnet_config['cidr'])
        pulumi.export(f"{subnet_id}_type", subnet_config['type'])
        if subnet_config['type'] == 'public':
            association = aws.ec2.RouteTableAssociation(f"public_route{x}",
                subnet_id=subnet.id,
                route_table_id=public_route.id)
            pulumi.export(f"public_route{x}", association.id)
    pulumi.export("vpc_id", vpc.id)

# Deploy VPC
stack = manage(args(), get_project_name(), pulumi_program)