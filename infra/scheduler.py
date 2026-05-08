"""EventBridge + Lambda: stop RDS staging at 20:00 UTC, start at 07:00 UTC (V32).

Only wired for env == "staging". Prod is never shut down.
"""

import json
import textwrap
from typing import Any

import pulumi
import pulumi_aws as aws

_STOP_SCHEDULE = "cron(0 20 * * ? *)"
_START_SCHEDULE = "cron(0 7 * * ? *)"


def create(
    env: str,
    db_out: dict[str, Any],
    opts: pulumi.ResourceOptions,
) -> None:
    lambda_role = aws.iam.Role(
        f"{env}-rds-scheduler-role",
        assume_role_policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
        ),
        opts=opts,
    )
    aws.iam.RolePolicyAttachment(
        f"{env}-rds-scheduler-basic",
        role=lambda_role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        opts=opts,
    )
    aws.iam.RolePolicy(
        f"{env}-rds-scheduler-rds-policy",
        role=lambda_role.name,
        policy=db_out["instance_id"].apply(
            lambda instance_id: json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": [
                                "rds:StopDBInstance",
                                "rds:StartDBInstance",
                                "rds:DescribeDBInstances",
                            ],
                            "Resource": f"arn:aws:rds:*:*:db:{instance_id}",
                        }
                    ],
                }
            )
        ),
        opts=opts,
    )

    handler_code = textwrap.dedent(
        """\
        import os
        import boto3

        rds = boto3.client("rds")
        INSTANCE_ID = os.environ["DB_INSTANCE_ID"]


        def handler(event, context):
            action = event.get("action")
            if action == "stop":
                rds.stop_db_instance(DBInstanceIdentifier=INSTANCE_ID)
            elif action == "start":
                rds.start_db_instance(DBInstanceIdentifier=INSTANCE_ID)
            else:
                raise ValueError(f"unknown action: {action}")
        """
    )

    fn = aws.lambda_.Function(
        f"{env}-rds-scheduler",
        runtime=aws.lambda_.Runtime.PYTHON3D12,
        handler="index.handler",
        role=lambda_role.arn,
        code=pulumi.AssetArchive(
            {
                "index.py": pulumi.StringAsset(handler_code),
            }
        ),
        environment=aws.lambda_.FunctionEnvironmentArgs(
            variables={"DB_INSTANCE_ID": db_out["instance_id"]}
        ),
        opts=opts,
    )

    for action, schedule in [("stop", _STOP_SCHEDULE), ("start", _START_SCHEDULE)]:
        rule = aws.cloudwatch.EventRule(
            f"{env}-rds-{action}-rule",
            schedule_expression=schedule,
            opts=opts,
        )
        aws.cloudwatch.EventTarget(
            f"{env}-rds-{action}-target",
            rule=rule.name,
            arn=fn.arn,
            input=json.dumps({"action": action}),
            opts=opts,
        )
        aws.lambda_.Permission(
            f"{env}-rds-{action}-permission",
            action="lambda:InvokeFunction",
            function=fn.name,
            principal="events.amazonaws.com",
            source_arn=rule.arn,
            opts=opts,
        )
