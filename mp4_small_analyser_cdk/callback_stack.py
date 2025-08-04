from aws_cdk import (
    Stack,
    aws_apigateway as apigw,
    aws_lambda as _lambda,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    RemovalPolicy,
    Duration,
    CfnOutput,
)
from constructs import Construct
import os


class CallbackStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Récupérer la configuration depuis les variables d'environnement
        table_name = os.getenv('DYNAMODB_TABLE_NAME', 'mp4-analyser-callback-results')
        lambda_timeout = int(os.getenv('LAMBDA_TIMEOUT', '30'))
        lambda_memory = int(os.getenv('LAMBDA_MEMORY_SIZE', '256'))
        api_stage = os.getenv('API_GATEWAY_STAGE', 'prod')
        project_name = os.getenv('PROJECT_NAME', 'mp4-small-analyser')
        environment = os.getenv('ENVIRONMENT', 'dev')

        # DynamoDB Table pour stocker les résultats des callbacks
        self.callback_results_table = dynamodb.Table(
            self, "CallbackResultsTable",
            table_name=f"{table_name}-{environment}",
            partition_key=dynamodb.Attribute(
                name="task_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,  # Pour les tests uniquement
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES
        )

        # Index secondaire global pour rechercher par batch_id
        self.callback_results_table.add_global_secondary_index(
            index_name="BatchIdIndex",
            partition_key=dynamodb.Attribute(
                name="batch_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.STRING
            )
        )

        # Fonction Lambda pour recevoir les callbacks
        self.callback_handler = _lambda.Function(
            self, "CallbackHandler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="callback_handler.lambda_handler",
            code=_lambda.Code.from_asset("lambda/callback"),
            timeout=Duration.seconds(lambda_timeout),
            memory_size=lambda_memory,
            environment={
                "CALLBACK_TABLE_NAME": self.callback_results_table.table_name,
                "BATCH_INDEX_NAME": "BatchIdIndex",
                "PROJECT_NAME": project_name,
                "ENVIRONMENT": environment
            },
            description=f"Handler callback pour {project_name} - {environment}"
        )

        # Permissions pour la Lambda d'écrire dans DynamoDB
        self.callback_results_table.grant_write_data(self.callback_handler)
        self.callback_results_table.grant_read_data(self.callback_handler)

        # API Gateway REST API
        self.api = apigw.RestApi(
            self, "CallbackApi",
            rest_api_name="MP4 Analyser Callback API",
            description="API pour recevoir les callbacks des analyses MP4",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            )
        )

        # Resource /callback
        callback_resource = self.api.root.add_resource("callback")
        
        # Resource /callback/{task_id}
        task_resource = callback_resource.add_resource("{task_id}")

        # POST /callback/{task_id} - Recevoir un callback
        task_resource.add_method(
            "POST",
            apigw.LambdaIntegration(
                self.callback_handler,
                proxy=True,
                integration_responses=[
                    apigw.IntegrationResponse(
                        status_code="200",
                        response_parameters={
                            "method.response.header.Access-Control-Allow-Origin": "'*'"
                        }
                    )
                ]
            ),
            method_responses=[
                apigw.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True
                    }
                )
            ]
        )

        # GET /callback/{task_id} - Récupérer le résultat d'un callback
        task_resource.add_method(
            "GET",
            apigw.LambdaIntegration(
                self.callback_handler,
                proxy=True
            )
        )

        # Resource /callback/batch/{batch_id}
        batch_resource = callback_resource.add_resource("batch").add_resource("{batch_id}")
        
        # GET /callback/batch/{batch_id} - Récupérer tous les résultats d'un batch
        batch_resource.add_method(
            "GET",
            apigw.LambdaIntegration(
                self.callback_handler,
                proxy=True
            )
        )

        # Export de l'URL de l'API
        CfnOutput(
            self, "CallbackApiUrl",
            value=self.api.url,
            description="URL de l'API callback"
        )
