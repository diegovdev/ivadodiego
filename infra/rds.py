"""RDS provisioning per environment.

preview: no RDS — SQLite via DATABASE_URL env var.
staging: Postgres t3.micro, single-AZ.
prod: Postgres t3.small, multi-AZ.
"""

from typing import Any

import pulumi
import pulumi_aws as aws


def create(
    env: str,
    net: dict[str, Any],
    opts: pulumi.ResourceOptions,
) -> dict[str, Any] | None:
    cfg = pulumi.Config()
    db_engine = cfg.get("db_engine") or "sqlite"

    if db_engine == "sqlite":
        return None

    instance_class = cfg.require("db_instance_class")
    multi_az = (cfg.get("db_multi_az") or "false").lower() == "true"

    subnet_group = aws.rds.SubnetGroup(
        f"{env}-rds-subnet-group",
        subnet_ids=net["private_subnet_ids"],
        opts=opts,
    )

    instance = aws.rds.Instance(
        f"{env}-rds",
        engine="postgres",
        engine_version="16",
        instance_class=instance_class,
        allocated_storage=20,
        db_name="museums",
        username="museums",
        manage_master_user_password=True,
        db_subnet_group_name=subnet_group.name,
        vpc_security_group_ids=[net["rds_sg_id"]],
        multi_az=multi_az,
        skip_final_snapshot=env != "prod",
        deletion_protection=env == "prod",
        backup_retention_period=7 if env == "prod" else 1,
        opts=opts,
    )

    return {
        "instance_id": instance.id,
        "endpoint": instance.endpoint,
        "master_user_secret_arn": instance.master_user_secrets[0].secret_arn,
    }
