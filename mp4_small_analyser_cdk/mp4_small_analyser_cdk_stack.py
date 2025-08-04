from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_iam as iam,
)
from constructs import Construct

class Mp4SmallAnalyserCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Créer notre propre Lambda Layer pour ffmpeg et requests
        ffmpeg_layer = _lambda.LayerVersion(
            self, "FFmpegLayer",
            code=_lambda.Code.from_asset("lambda/layers/ffmpeg"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            description="FFmpeg et FFprobe binaires avec le package requests pour Python"
        )

        # Lambda pour l'analyse MP4 individuelle (travailleur)
        self.mp4_analyser_lambda = _lambda.Function(
            self, "MP4AnalyserFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="mp4_analyser_handler.lambda_handler",
            code=_lambda.Code.from_asset("lambda/mp4_analyser"),
            timeout=Duration.minutes(2),  # 2 minutes pour les analyses plus longues
            memory_size=2048,  # Plus de mémoire pour ffmpeg et téléchargement
            layers=[ffmpeg_layer],  # Ajouter le layer ffmpeg
            environment={
                'LOG_LEVEL': 'INFO'
            }
        )

        # Lambda dispatcher pour lancer les analyses MP4 de façon asynchrone
        self.mp4_dispatcher_lambda = _lambda.Function(
            self, "MP4DispatcherFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="mp4_dispatcher_handler.lambda_handler",
            code=_lambda.Code.from_asset("lambda/mp4_dispatcher"),
            timeout=Duration.seconds(30),  # Rapide, juste pour lancer l'analyse
            memory_size=256,  # Peu de ressources nécessaires
            environment={
                'MP4_LAMBDA_NAME': self.mp4_analyser_lambda.function_name,
                'LOG_LEVEL': 'INFO'
            }
        )

        # Lambda pour le traitement en batch
        self.batch_lambda = _lambda.Function(
            self, "BatchFunction", 
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="batch_handler.lambda_handler",
            code=_lambda.Code.from_asset("lambda/batch"),
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={
                'MP4_LAMBDA_NAME': self.mp4_analyser_lambda.function_name,
                'LOG_LEVEL': 'INFO'
            }
        )

        # Permissions pour que les Lambdas puissent s'invoquer
        self.mp4_analyser_lambda.grant_invoke(self.mp4_dispatcher_lambda)
        self.mp4_analyser_lambda.grant_invoke(self.batch_lambda)

        # API Gateway
        self.api = apigw.RestApi(
            self, "MP4AnalyserApi",
            rest_api_name="MP4 Small Analyser API",
            description="API pour l'analyse MP4 et le traitement en batch",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            )
        )

        # Route POST /mp4_small_analyser - Dispatch d'analyse individuelle
        mp4_resource = self.api.root.add_resource("mp4_small_analyser")
        mp4_resource.add_method(
            "POST",
            apigw.LambdaIntegration(
                self.mp4_dispatcher_lambda,
                proxy=True
            )
        )

        # Route POST /batch - Traitement en batch
        batch_resource = self.api.root.add_resource("batch")
        batch_resource.add_method(
            "POST", 
            apigw.LambdaIntegration(
                self.batch_lambda,
                proxy=True
            )
        )

        # Outputs
        CfnOutput(
            self, "MP4AnalyserApiUrl",
            value=self.api.url,
            description="URL de l'API MP4 Small Analyser"
        )

        CfnOutput(
            self, "MP4AnalyserLambdaName", 
            value=self.mp4_analyser_lambda.function_name,
            description="Nom de la Lambda MP4 analyser"
        )

        CfnOutput(
            self, "MP4DispatcherLambdaName", 
            value=self.mp4_dispatcher_lambda.function_name,
            description="Nom de la Lambda MP4 dispatcher"
        )

        CfnOutput(
            self, "BatchLambdaName",
            value=self.batch_lambda.function_name,
            description="Nom de la Lambda batch"
        )
