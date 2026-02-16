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
