import os
from pathlib import Path
from typing import Dict

CDK_REQUIREMENTS = """\
aws-cdk-lib==2.132.0
constructs>=10.0.0,<11.0.0
boto3
pytest
"""

APP_PY = """\
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
"""

STACK_PY = """\
from aws_cdk import (
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigateway as apigw,
    aws_lambda as _lambda,
    aws_dynamodb as ddb,
)
from constructs import Construct

class AlertsApiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        table = ddb.Table(
            self, "AlertsTable",
            partition_key=ddb.Attribute(name="PK", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="SK", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        fn = _lambda.Function(
            self, "AlertsHandler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.health",
            code=_lambda.Code.from_asset("../services/customer-alerts"),
            timeout=Duration.seconds(10),
            environment={
                "TABLE_NAME": table.table_name,
            },
        )
        table.grant_read_write_data(fn)

        api = apigw.RestApi(
            self, "AlertsApi",
            deploy=True,
            cloud_watch_role=True,
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=["GET","POST","PATCH","OPTIONS"]
            )
        )

        base = api.root.add_resource("api")
        base.add_resource("health").add_method("GET", apigw.LambdaIntegration(fn))

        # NOTE: The handler currently routes only /health.
        # After you implement alert routes in handler.py, split functions or add Lambda proxy.
        alerts = base.add_resource("alerts")
        alerts.add_method("GET", apigw.LambdaIntegration(fn))
        alerts.add_method("POST", apigw.LambdaIntegration(fn))
        alert_id = alerts.add_resource("{id}")
        alert_id.add_method("PATCH", apigw.LambdaIntegration(fn))

        self.api_url = api.url

        # Output is visible in 'cdk deploy'
        from aws_cdk import CfnOutput
        CfnOutput(self, "ApiBaseUrl", value=api.url)
"""

PYPROJECT_TOML = """\
[tool.pytest.ini_options]
pythonpath = ["services/customer-alerts"]
"""

GHA_WORKFLOW = """\
name: ci-cd

on:
  push:
    branches: [ "main", "master" ]
  pull_request:

jobs:
  build-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install service deps & run tests
        working-directory: services/customer-alerts
        run: |
          python -m pip install -U pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          pip install pytest
          pytest -q

  cdk-deploy:
    needs: build-test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/master'
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_CDK_ROLE_ARN }}
          aws-region: ${{ secrets.AWS_DEFAULT_REGION || 'us-east-1' }}

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install CDK and deps
        run: |
          npm i -g aws-cdk
          python -m pip install -U pip
          python -m pip install -r infra/cdk/requirements.txt

      - name: CDK synth
        working-directory: infra/cdk
        run: cdk synth

      - name: CDK deploy
        working-directory: infra/cdk
        run: cdk deploy --require-approval never
"""

class DevOpsIacAgent:
    """
    Generates a CDK (Python) app and a GitHub Actions workflow for CI/CD.
    """
    def __init__(self, cdk_dir: str = "infra/cdk"):
        self.cdk_dir = Path(cdk_dir)

    def run(self, input: Dict):
        """
        input keys (optional):
          region: str
          service_dir: str
        """
        region = input.get("region", "us-east-1")
        service_dir = Path(input.get("service_dir", "services/customer-alerts"))

        # Create CDK skeleton
        (self.cdk_dir / "stacks").mkdir(parents=True, exist_ok=True)
        (self.cdk_dir / "requirements.txt").write_text(CDK_REQUIREMENTS, encoding="utf-8")
        (self.cdk_dir / "app.py").write_text(APP_PY, encoding="utf-8")
        (self.cdk_dir / "stacks" / "alerts_api_stack.py").write_text(STACK_PY, encoding="utf-8")
        (self.cdk_dir / "pyproject.toml").write_text(PYPROJECT_TOML, encoding="utf-8")

        # Ensure service dir exists
        service_dir.mkdir(parents=True, exist_ok=True)

        # GitHub Actions workflow
        workflows = Path(".github/workflows")
        workflows.mkdir(parents=True, exist_ok=True)
        (workflows / "ci-cd.yml").write_text(GHA_WORKFLOW, encoding="utf-8")

        return {
            "status": "ok",
            "cdk_dir": str(self.cdk_dir),
            "workflow": ".github/workflows/ci-cd.yml",
            "notes": [
                "Set GitHub secret AWS_CDK_ROLE_ARN to an IAM Role ARN trusted for GitHub OIDC.",
                "Set AWS_DEFAULT_REGION secret if different from us-east-1.",
                "Run: npm i -g aws-cdk && pip install -r infra/cdk/requirements.txt && cdk bootstrap"
            ]
        }