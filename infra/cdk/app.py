#!/usr/bin/env python3
import os
import aws_cdk as cdk
from stacks.alerts_api_stack import AlertsApiStack

app = cdk.App()

env = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT"),
    region=os.getenv("CDK_DEFAULT_REGION", "us-east-1"),
)

AlertsApiStack(app, "AlertsApiStack", env=env)

app.synth()
