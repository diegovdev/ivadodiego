"""CloudWatch alarms: 5xx rate, p99 latency, ECS under-capacity, RDS CPU."""

from typing import Any

import pulumi
import pulumi_aws as aws


def create(
    env: str,
    net: dict[str, Any],
    svc: dict[str, Any],
    db_out: dict[str, Any] | None,
    opts: pulumi.ResourceOptions,
) -> None:
    cfg = pulumi.Config()
    sns_arn = cfg.get("alerts_sns_arn")
    alarm_actions = [sns_arn] if sns_arn else []

    # Resolve both cluster_name and service_name before building alarms (B35).
    pulumi.Output.all(
        cluster_name=svc["cluster_name"],
        service_name=svc["service_name"],
    ).apply(
        lambda args: _ecs_alarms(
            env, args["cluster_name"], args["service_name"], alarm_actions, opts
        )
    )

    if svc.get("alb_arn_suffix"):
        svc["alb_arn_suffix"].apply(
            lambda suffix: _alb_alarms(env, suffix, alarm_actions, opts)
        )

    if db_out:
        db_out["instance_id"].apply(
            lambda instance_id: _rds_alarms(env, instance_id, alarm_actions, opts)
        )


def _alb_alarms(
    env: str,
    alb_arn_suffix: str,
    alarm_actions: list[str],
    opts: pulumi.ResourceOptions,
) -> None:
    dimensions = {"LoadBalancer": alb_arn_suffix}

    aws.cloudwatch.MetricAlarm(
        f"{env}-alb-5xx-rate",
        comparison_operator="GreaterThanThreshold",
        evaluation_periods=2,
        metric_name="HTTPCode_ELB_5XX_Count",
        namespace="AWS/ApplicationELB",
        period=60,
        statistic="Sum",
        threshold=10,
        alarm_description="ALB 5xx count > 10 per minute for 2 minutes",
        dimensions=dimensions,
        alarm_actions=alarm_actions,
        treat_missing_data="notBreaching",
        opts=opts,
    )

    aws.cloudwatch.MetricAlarm(
        f"{env}-alb-p99-latency",
        comparison_operator="GreaterThanThreshold",
        evaluation_periods=2,
        metric_name="TargetResponseTime",
        namespace="AWS/ApplicationELB",
        period=60,
        extended_statistic="p99",
        threshold=2.0,
        alarm_description="ALB p99 response time > 2s for 2 minutes",
        dimensions=dimensions,
        alarm_actions=alarm_actions,
        treat_missing_data="notBreaching",
        opts=opts,
    )


def _ecs_alarms(
    env: str,
    cluster_name: str,
    service_name: str,
    alarm_actions: list[str],
    opts: pulumi.ResourceOptions,
) -> None:
    dimensions = {"ClusterName": cluster_name, "ServiceName": service_name}

    aws.cloudwatch.MetricAlarm(
        f"{env}-ecs-cpu-high",
        comparison_operator="GreaterThanThreshold",
        evaluation_periods=2,
        metric_name="CPUUtilization",
        namespace="AWS/ECS",
        period=60,
        statistic="Average",
        threshold=80,
        alarm_description="ECS CPU > 80% for 2 minutes",
        dimensions=dimensions,
        alarm_actions=alarm_actions,
        opts=opts,
    )

    aws.cloudwatch.MetricAlarm(
        f"{env}-ecs-running-tasks-low",
        comparison_operator="LessThanThreshold",
        evaluation_periods=1,
        metric_name="RunningTaskCount",
        namespace="ECS/ContainerInsights",
        period=60,
        statistic="Average",
        threshold=1,
        alarm_description="ECS running task count below 1",
        dimensions=dimensions,
        alarm_actions=alarm_actions,
        opts=opts,
    )


def _rds_alarms(
    env: str,
    instance_id: str,
    alarm_actions: list[str],
    opts: pulumi.ResourceOptions,
) -> None:
    dimensions = {"DBInstanceIdentifier": instance_id}

    aws.cloudwatch.MetricAlarm(
        f"{env}-rds-cpu-high",
        comparison_operator="GreaterThanThreshold",
        evaluation_periods=2,
        metric_name="CPUUtilization",
        namespace="AWS/RDS",
        period=60,
        statistic="Average",
        threshold=80,
        alarm_description="RDS CPU > 80% for 2 minutes",
        dimensions=dimensions,
        alarm_actions=alarm_actions,
        opts=opts,
    )
