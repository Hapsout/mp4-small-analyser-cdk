#!/usr/bin/env python3
import os
from dotenv import load_dotenv

import aws_cdk as cdk

from mp4_small_analyser_cdk.mp4_small_analyser_cdk_stack import Mp4SmallAnalyserCdkStack
from mp4_small_analyser_cdk.callback_stack import CallbackStack

# Charger la configuration depuis .env si disponible
load_dotenv()

app = cdk.App()

# Récupérer la configuration depuis les variables d'environnement
aws_account = os.getenv('AWS_ACCOUNT_ID')
aws_region = os.getenv('AWS_REGION')
project_name = os.getenv('PROJECT_NAME', 'mp4-small-analyser')
environment = os.getenv('ENVIRONMENT', 'dev')
main_stack_name = os.getenv('MAIN_STACK_NAME', 'Mp4SmallAnalyserCdkStack')
callback_stack_name = os.getenv('CALLBACK_STACK_NAME', 'Mp4AnalyserCallbackStack')

# Configuration des tags
client = os.getenv('CLIENT', 'default-client')
project = os.getenv('PROJECT', 'mp4-small-analyser')

# Tags communs pour toutes les ressources
common_tags = {
    'Environment': environment,
    'Project': project,
    'Client': client,
    'ManagedBy': 'AWS-CDK',
    'Owner': 'MP4-Small-Analyser'
}

# Configuration de l'environnement CDK
cdk_env = None
if aws_account and aws_region:
    cdk_env = cdk.Environment(account=aws_account, region=aws_region)
    print(f"🌍 Déploiement configuré pour: {aws_account} dans {aws_region}")
else:
    print("⚠️  Pas de configuration AWS spécifique - déploiement agnostique")

# Stack principale (vide pour l'instant)
main_stack = Mp4SmallAnalyserCdkStack(
    app, 
    main_stack_name,
    env=cdk_env,
    description=f"Stack principale pour {project_name} - environnement {environment}"
)

# Stack de callback pour recevoir les résultats des analyses
callback_stack = CallbackStack(
    app, 
    callback_stack_name,
    env=cdk_env,
    description=f"Stack callback API pour {project_name} - environnement {environment}"
)

# Appliquer les tags communs à toutes les stacks
for tag_key, tag_value in common_tags.items():
    cdk.Tags.of(main_stack).add(tag_key, tag_value)
    cdk.Tags.of(callback_stack).add(tag_key, tag_value)

app.synth()
