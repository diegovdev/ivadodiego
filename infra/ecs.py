"""ECS Fargate cluster, task definition, and service per environment.

preview: public IP, no ALB.
staging/prod: behind ALB; desired_count from stack config.
"""

import json
from typing import Any

import pulumi
import pulumi_aws as aws


def create(
    env: str,
    net: dict[str, Any],
    db_out: dict[str, Any] | None,
    secret_arn: pulumi.Output[str] | None,
    image_uri: str,
    opts: pulumi.ResourceOptions,
) -> dict[str, Any]:
    cfg = pulumi.Config()
    task_cpu = cfg.get("task_cpu") or "256"
    task_memory = cfg.get("task_memory") or "512"
    desired_count = int(cfg.get("desired_count") or "1")
    enable_alb = (cfg.get("enable_alb") or "false").lower() == "true"

    cluster = aws.ecs.Cluster(f"{env}-cluster", opts=opts)

    exec_role = aws.iam.Role(
        f"{env}-ecs-exec-role",
        assume_role_policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
        ),
        opts=opts,
    )
    aws.iam.RolePolicyAttachment(
        f"{env}-ecs-exec-policy",
        role=exec_role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
        opts=opts,
    )
    if secret_arn:
        aws.iam.RolePolicy(
            f"{env}-ecs-secret-policy",
            role=exec_role.name,
            policy=secret_arn.apply(
                lambda arn: json.dumps(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": "secretsmanager:GetSecretValue",
                                "Resource": arn,
                            }
                        ],
                    }
                )
            ),
            opts=opts,
        )

    log_group = aws.cloudwatch.LogGroup(
        f"/ecs/{env}/museums-api",
        retention_in_days=14,
        opts=opts,
    )

    env_vars: list[dict[str, str]] = [
        {"name": "LOG_LEVEL", "value": "INFO"},
        {"name": "MODEL_PATH", "value": "/data/models/regression.pkl"},
    ]
    container_secrets: list[dict[str, str]] = []
    if secret_arn:
        container_secrets.append(
            {"name": "DATABASE_URL", "valueFrom": secret_arn}  # type: ignore[dict-item]
        )
    else:
        env_vars.append(
            {"name": "DATABASE_URL", "value": "sqlite:////data/museums.db"}
        )

    container_def = pulumi.Output.all(
        image_uri=image_uri,
        log_group=log_group.name,
        env_vars=env_vars,
        secrets=container_secrets if secret_arn else [],
    ).apply(
        lambda args: json.dumps(
            [
                {
                    "name": "api",
                    "image": args["image_uri"],
                    "portMappings": [{"containerPort": 8000, "protocol": "tcp"}],
                    "environment": args["env_vars"],
                    "secrets": args["secrets"],
                    "logConfiguration": {
                        "logDriver": "awslogs",
                        "options": {
                            "awslogs-group": args["log_group"],
                            "awslogs-region": "us-east-1",
                            "awslogs-stream-prefix": "api",
                        },
                    },
                    "healthCheck": {
                        "command": [
                            "CMD",
                            "python",
                            "-c",
                            "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')",
                        ],
                        "interval": 10,
                        "timeout": 5,
                        "retries": 3,
                        "startPeriod": 15,
                    },
                }
            ]
        )
    )

    task_def = aws.ecs.TaskDefinition(
        f"{env}-task",
        family=f"museums-{env}",
        cpu=task_cpu,
        memory=task_memory,
        network_mode="awsvpc",
        requires_compatibilities=["FARGATE"],
        execution_role_arn=exec_role.arn,
        container_definitions=container_def,
        opts=opts,
    )

    if enable_alb:
        alb = aws.alb.LoadBalancer(
            f"{env}-alb",
            internal=False,
            load_balancer_type="application",
            security_groups=[net["alb_sg_id"]],
            subnets=net["public_subnet_ids"],
            opts=opts,
        )
        tg = aws.alb.TargetGroup(
            f"{env}-tg",
            port=8000,
            protocol="HTTP",
            target_type="ip",
            vpc_id=net["vpc_id"],
            health_check=aws.alb.TargetGroupHealthCheckArgs(
                path="/health",
                healthy_threshold=2,
                unhealthy_threshold=3,
                interval=10,
                timeout=5,
            ),
            opts=opts,
        )
        aws.alb.Listener(
            f"{env}-listener",
            load_balancer_arn=alb.arn,
            port=80,
            protocol="HTTP",
            default_actions=[
                aws.alb.ListenerDefaultActionArgs(type="forward", target_group_arn=tg.arn)
            ],
            opts=opts,
        )
        load_balancers = [
            aws.ecs.ServiceLoadBalancerArgs(
                target_group_arn=tg.arn,
                container_name="api",
                container_port=8000,
            )
        ]
        service_url: pulumi.Output[str] = alb.dns_name
        alb_arn_suffix: pulumi.Output[str] | None = alb.arn_suffix
    else:
        load_balancers = []
        service_url = pulumi.Output.from_input("http://localhost:8000")
        alb_arn_suffix = None

    service = aws.ecs.Service(
        f"{env}-service",
        cluster=cluster.arn,
        task_definition=task_def.arn,
        desired_count=desired_count,
        launch_type="FARGATE",
        network_configuration=aws.ecs.ServiceNetworkConfigurationArgs(
            subnets=net["private_subnet_ids"] if enable_alb else net["public_subnet_ids"],
            security_groups=[net["api_sg_id"]],
            assign_public_ip=not enable_alb,
        ),
        load_balancers=load_balancers,
        opts=opts,
    )

    return {
        "cluster_name": cluster.name,
        "service_name": service.name,
        "url": service_url,
        "log_group": log_group.name,
        "alb_arn_suffix": alb_arn_suffix,
    }
