"""Museums API — Pulumi entrypoint.

Stack config keys (all under museums:):
  env           preview | staging | prod
  region        AWS region (default us-east-1)
  image_uri     ECR image URI for the API container
"""

import ecs
import monitoring
import networking
import pulumi
import pulumi_aws as aws
import rds
import scheduler
import secretsmgr as sec

cfg = pulumi.Config()
env: str = cfg.require("env")
region: str = cfg.get("region") or "us-east-1"
image_uri: str = cfg.require("image_uri")

aws_provider = aws.Provider("aws", region=region)
provider_opts = pulumi.ResourceOptions(provider=aws_provider)

net = networking.create(env, provider_opts)
db_out = rds.create(env, net, provider_opts)
secret_arn = sec.create(env, db_out, provider_opts) if db_out else None
svc = ecs.create(env, net, db_out, secret_arn, image_uri, provider_opts)
monitoring.create(env, net, svc, db_out, provider_opts)

if env == "staging" and db_out:
    scheduler.create(env, db_out, provider_opts)

pulumi.export("env", env)
pulumi.export("service_url", svc["url"])
