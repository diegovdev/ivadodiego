"""VPC, subnets, and security groups per environment.

preview: default VPC + public subnets (public IP, no ALB).
staging/prod: dedicated VPC with public (ALB) + private (ECS/RDS) subnets across 3 AZs.
"""

from typing import Any

import pulumi
import pulumi_aws as aws

_AZS = ["a", "b", "c"]


def create(env: str, region: str, opts: pulumi.ResourceOptions) -> dict[str, Any]:
    if env == "preview":
        return _preview_networking(opts)
    return _dedicated_networking(env, region, opts)


def _preview_networking(opts: pulumi.ResourceOptions) -> dict[str, Any]:
    vpc = aws.ec2.get_default_vpc()
    subnets = aws.ec2.get_subnets(
        filters=[aws.ec2.GetSubnetsFilterArgs(name="vpc-id", values=[vpc.id])]
    )
    sg = aws.ec2.SecurityGroup(
        "preview-api-sg",
        vpc_id=vpc.id,
        ingress=[
            aws.ec2.SecurityGroupIngressArgs(
                protocol="tcp", from_port=8000, to_port=8000, cidr_blocks=["0.0.0.0/0"]
            )
        ],
        egress=[
            aws.ec2.SecurityGroupEgressArgs(
                protocol="-1", from_port=0, to_port=0, cidr_blocks=["0.0.0.0/0"]
            )
        ],
        opts=opts,
    )
    return {
        "vpc_id": vpc.id,
        "public_subnet_ids": subnets.ids,
        "private_subnet_ids": subnets.ids,
        "api_sg_id": sg.id,
        "alb_sg_id": None,
        "rds_sg_id": None,
    }


def _dedicated_networking(env: str, region: str, opts: pulumi.ResourceOptions) -> dict[str, Any]:
    vpc = aws.ec2.Vpc(
        f"{env}-vpc",
        cidr_block="10.0.0.0/16",
        enable_dns_hostnames=True,
        enable_dns_support=True,
        opts=opts,
    )
    igw = aws.ec2.InternetGateway(f"{env}-igw", vpc_id=vpc.id, opts=opts)
    public_rt = aws.ec2.RouteTable(
        f"{env}-public-rt",
        vpc_id=vpc.id,
        routes=[
            aws.ec2.RouteTableRouteArgs(cidr_block="0.0.0.0/0", gateway_id=igw.id)
        ],
        opts=opts,
    )

    public_subnets: list[aws.ec2.Subnet] = []
    private_subnets: list[aws.ec2.Subnet] = []

    for i, az in enumerate(_AZS):
        pub = aws.ec2.Subnet(
            f"{env}-pub-{az}",
            vpc_id=vpc.id,
            cidr_block=f"10.0.{i}.0/24",
            availability_zone=f"{region}{az}",
            map_public_ip_on_launch=True,
            opts=opts,
        )
        aws.ec2.RouteTableAssociation(
            f"{env}-pub-rta-{az}", subnet_id=pub.id, route_table_id=public_rt.id, opts=opts
        )
        public_subnets.append(pub)

        priv = aws.ec2.Subnet(
            f"{env}-priv-{az}",
            vpc_id=vpc.id,
            cidr_block=f"10.0.{i + 10}.0/24",
            availability_zone=f"{region}{az}",
            opts=opts,
        )
        private_subnets.append(priv)

    alb_sg = aws.ec2.SecurityGroup(
        f"{env}-alb-sg",
        vpc_id=vpc.id,
        ingress=[
            aws.ec2.SecurityGroupIngressArgs(
                protocol="tcp", from_port=80, to_port=80, cidr_blocks=["0.0.0.0/0"]
            ),
            aws.ec2.SecurityGroupIngressArgs(
                protocol="tcp", from_port=443, to_port=443, cidr_blocks=["0.0.0.0/0"]
            ),
        ],
        egress=[
            aws.ec2.SecurityGroupEgressArgs(
                protocol="-1", from_port=0, to_port=0, cidr_blocks=["0.0.0.0/0"]
            )
        ],
        opts=opts,
    )
    api_sg = aws.ec2.SecurityGroup(
        f"{env}-api-sg",
        vpc_id=vpc.id,
        ingress=[
            aws.ec2.SecurityGroupIngressArgs(
                protocol="tcp",
                from_port=8000,
                to_port=8000,
                security_groups=[alb_sg.id],
            )
        ],
        egress=[
            aws.ec2.SecurityGroupEgressArgs(
                protocol="-1", from_port=0, to_port=0, cidr_blocks=["0.0.0.0/0"]
            )
        ],
        opts=opts,
    )
    rds_sg = aws.ec2.SecurityGroup(
        f"{env}-rds-sg",
        vpc_id=vpc.id,
        ingress=[
            aws.ec2.SecurityGroupIngressArgs(
                protocol="tcp",
                from_port=5432,
                to_port=5432,
                security_groups=[api_sg.id],
            )
        ],
        egress=[
            aws.ec2.SecurityGroupEgressArgs(
                protocol="-1", from_port=0, to_port=0, cidr_blocks=["0.0.0.0/0"]
            )
        ],
        opts=opts,
    )
    return {
        "vpc_id": vpc.id,
        "public_subnet_ids": [s.id for s in public_subnets],
        "private_subnet_ids": [s.id for s in private_subnets],
        "api_sg_id": api_sg.id,
        "alb_sg_id": alb_sg.id,
        "rds_sg_id": rds_sg.id,
    }
