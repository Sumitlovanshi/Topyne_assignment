import pulumi
import pulumi_aws as aws

# Create VPC and subnets
vpc = aws.ec2.Vpc(
    "my-vpc",
    cidr_block="10.0.0.0/16",
)

public_subnet = aws.ec2.Subnet(
    "public-subnet",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    availability_zone="us-west-2a",
    tags={
        "Name": "public-subnet",
    },
)

private_subnet_1 = aws.ec2.Subnet(
    "private-subnet-1",
    vpc_id=vpc.id,
    cidr_block="10.0.2.0/24",
    availability_zone="us-west-2b",
    tags={
        "Name": "private-subnet-1",
    },
)

private_subnet_2 = aws.ec2.Subnet(
    "private-subnet-2",
    vpc_id=vpc.id,
    cidr_block="10.0.3.0/24",
    availability_zone="us-west-2c",
    tags={
        "Name": "private-subnet-2",
    },
)

# Create Internet Gateway and attach to VPC
internet_gateway = aws.ec2.InternetGateway(
    "internet-gateway",
    vpc_id=vpc.id,
)

# Create route table for public subnet and add route to Internet Gateway
public_route_table = aws.ec2.RouteTable(
    "public-route-table",
    vpc_id=vpc.id,
    routes=[{
        "cidr_block": "0.0.0.0/0",
        "gateway_id": internet_gateway.id,
    }],
    tags={
        "Name": "public-route-table",
    },
)

public_route_table_association = aws.ec2.RouteTableAssociation(
    "public-route-table-association",
    subnet_id=public_subnet.id,
    route_table_id=public_route_table.id,
)

# Create security group for NGINX containers
nginx_security_group = aws.ec2.SecurityGroup(
    "nginx-security-group",
    vpc_id=vpc.id,
    ingress=[{
        "protocol": "tcp",
        "from_port": 80,
        "to_port": 80,
        "cidr_blocks": ["0.0.0.0/0"],
    }],
)


# Create Launch Configuration for EC2 instances
launch_configuration = aws.ec2.LaunchConfiguration(
    "my-launch-config",
    image_id="ami-0c55b159cbfafe1f0",
    instance_type="t2.micro",
    security_groups=[nginx_security_group.id],
    user_data="""#!/bin/bash
sudo yum update -y
sudo yum install -y docker
sudo service docker start
sudo docker run -d -p 80:80 nginx
""",
)

# Create Auto Scaling Group and attach Launch Configuration
auto_scaling_group = aws.autoscaling.Group(
    "my-auto-scaling-group",
    desired_capacity=2,
    max_size=4,
    min_size=2,
    launch_configuration=launch_configuration.id,
    vpc_zone_identifiers=[private_subnet_1.id, private_subnet_2.id],
    tags=[{
        "key": "Name",
        "value": "nginx-autoscaling-group",
        "propagate_at_launch": True,
    }],
)

load_balancer = aws.lb.LoadBalancer(
    "my-load-balancer",
    load_balancer_type="application",
    security_groups=[nginx_security_group.id],
    subnets=[public_subnet.id, private_subnet_1.id, private_subnet_2.id],
)



target_group = aws.lb.TargetGroup(
    "my-target-group",
    port=80,
    protocol="HTTP",
    target_type="instance",
    vpc_id=vpc.id,
)

# Create listener for Load Balancer and attach Target Group
listener = aws.lb.Listener(
    "my-listener",
    load_balancer_arn=load_balancer.arn,
    port=80,
    default_actions=[{
        "type": "forward",
        "target_group_arn": target_group.arn,
    }],
)

# Output Load Balancer DNS Name
pulumi.export("load_balancer_dns_name", load_balancer.dns_name)
