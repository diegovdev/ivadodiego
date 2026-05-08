"""Secrets Manager: configure 7-day rotation for RDS master password (V33).

RDS `manage_master_user_password=True` already creates the secret in Secrets Manager.
This module attaches a rotation schedule to that secret (7-day cadence) and returns
the secret ARN for injection into the ECS task definition via the `secrets` field.
"""

from typing import Any

import pulumi
import pulumi_aws as aws


def create(
    env: str,
    db_out: dict[str, Any],
    opts: pulumi.ResourceOptions,
) -> pulumi.Output[str]:
    secret_arn: pulumi.Output[str] = db_out["master_user_secret_arn"]

    # Attach 7-day automatic rotation — RDS-managed secret uses the
    # aws-secretsmanager-rotation Lambda for the RDS Postgres single-user strategy.
    aws.secretsmanager.SecretRotation(
        f"{env}-rds-rotation",
        secret_id=secret_arn,
        rotation_rules=aws.secretsmanager.SecretRotationRotationRulesArgs(
            automatically_after_days=7,
        ),
        opts=opts,
    )

    return secret_arn
