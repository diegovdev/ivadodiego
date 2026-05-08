"""Secrets Manager: surface ARN for the RDS-managed master-user secret (V33).

RDS `manage_master_user_password=True` owns the secret lifecycle and rotates it
automatically every 7 days.  Attaching a separate `SecretRotation` resource to a
secret that is already managed by another service causes AWS to reject the call with
ResourceNotFoundException / InvalidRequestException — so we intentionally omit it.
The 7-day default rotation satisfies V33 without an explicit rotation resource.
"""

from typing import Any

import pulumi


def create(
    env: str,
    db_out: dict[str, Any],
    opts: pulumi.ResourceOptions,
) -> pulumi.Output[str]:
    # AWS auto-rotates RDS-managed secrets every 7 days by default (V33).
    return db_out["master_user_secret_arn"]
