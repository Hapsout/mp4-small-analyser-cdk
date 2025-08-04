import json
import boto3
import logging
import uuid
import os

# Configuration du logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Client Lambda
lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
    """
    Handler pour lancer une analyse MP4 de façon asynchrone
    """
    try:
        # Parser le body de la requête
        if event.get('body'):
            request_data = json.loads(event['body'])
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Body de requête manquant'}),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
        
        # Valider les paramètres requis
        file_url = request_data.get('file_url')
        callback_url = request_data.get('callback_url')
        
        if not file_url or not callback_url:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'file_url et callback_url sont requis'
                }),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
        
        # Auto-générer task_id s'il n'est pas fourni
        task_id = request_data.get('task_id')
        if not task_id or not task_id.strip():
            task_id = str(uuid.uuid4())
        
        # Auto-générer batch_id s'il n'est pas fourni
        batch_id = request_data.get('batch_id')
        if not batch_id or not batch_id.strip():
            batch_id = str(uuid.uuid4())
        
        # Ajouter les IDs générés aux données
        request_data_with_ids = {
            **request_data,
            'task_id': task_id,
            'batch_id': batch_id
        }
        
        # Récupérer le nom de la Lambda MP4 analyser depuis les variables d'environnement
        mp4_lambda_name = os.environ.get('MP4_LAMBDA_NAME')
        if not mp4_lambda_name:
            raise ValueError("MP4_LAMBDA_NAME non configuré dans les variables d'environnement")
        
        # Préparer le payload comme si c'était une requête API Gateway
        payload = {
            'httpMethod': 'POST',
            'body': json.dumps(request_data_with_ids),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
        # Invoquer la Lambda MP4 analyser de manière asynchrone
        response = lambda_client.invoke(
            FunctionName=mp4_lambda_name,
            InvocationType='Event',  # Asynchrone
            Payload=json.dumps(payload)
        )
        
        # Vérifier le status code de l'invocation
        if response['StatusCode'] == 202:  # Accepted pour invocation asynchrone
            logger.info(f"Analyse MP4 lancée avec succès pour task_id: {task_id}")
            
            return {
                'statusCode': 202,  # Accepted
                'body': json.dumps({
                    'message': 'Analyse lancée avec succès de manière asynchrone',
                    'task_id': task_id,
                    'batch_id': batch_id,
                    'status': 'processing',
                    'callback_url': callback_url
                }),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
        else:
            logger.error(f"Erreur lors de l'invocation Lambda: status {response['StatusCode']}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': f"Erreur d'invocation Lambda: status {response['StatusCode']}"
                }),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
            
    except Exception as e:
        logger.error(f"Erreur dans lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Erreur lors du lancement de l\'analyse: {str(e)}'}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
