import json
import boto3
import os
from datetime import datetime
from decimal import Decimal
import logging
import uuid

# Configuration du logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Clients AWS
dynamodb = boto3.resource('dynamodb')
table_name = os.environ['CALLBACK_TABLE_NAME']
batch_index_name = os.environ['BATCH_INDEX_NAME']
table = dynamodb.Table(table_name)


def lambda_handler(event, context):
    """
    Handler principal pour gérer les requêtes de callback
    """
    try:
        http_method = event['httpMethod']
        path = event['path']
        
        logger.info(f"Méthode: {http_method}, Chemin: {path}")
        
        if http_method == 'POST':
            return handle_callback_post(event, context)
        elif http_method == 'GET':
            if '/batch/' in path:
                return handle_batch_get(event, context)
            else:
                return handle_callback_get(event, context)
        else:
            return {
                'statusCode': 405,
                'body': json.dumps({'error': 'Méthode non autorisée'}),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
            
    except Exception as e:
        logger.error(f"Erreur dans lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Erreur interne du serveur'}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }


def handle_callback_post(event, context):
    """
    Gère les callbacks POST pour enregistrer les résultats d'analyse
    """
    try:
        # Extraire task_id du path ou le générer s'il n'existe pas
        path_task_id = event.get('pathParameters', {}).get('task_id')
        
        # Parser le body de la requête
        if event.get('body'):
            callback_data = json.loads(event['body'])
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Body de requête manquant'}),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
        
        # Auto-générer task_id si non fourni
        task_id = path_task_id or callback_data.get('task_id') or str(uuid.uuid4())
        
        # Auto-générer batch_id si non fourni dans la payload
        batch_id = callback_data.get('batch_id')
        if not batch_id or not batch_id.strip():
            batch_id = str(uuid.uuid4())
        
        # Timestamp
        timestamp = datetime.utcnow().isoformat()
        
        # Préparer l'item pour DynamoDB avec task_id comme partition key
        # Convertir processing_time en Decimal pour DynamoDB
        processing_time = callback_data.get('processing_time', 0)
        if isinstance(processing_time, (int, float)):
            processing_time = Decimal(str(processing_time))
        
        item = {
            'task_id': task_id,  # Partition key
            'batch_id': batch_id,  # Sera utilisé pour les requêtes batch
            'timestamp': timestamp,
            'status': callback_data.get('status', 'unknown'),
            'file_url': callback_data.get('file_url', ''),
            'analysis_results': json.dumps(callback_data.get('results', {}), default=str),
            'error_message': callback_data.get('error', ''),
            'processing_time': processing_time,
            'metadata': json.dumps(callback_data.get('metadata', {}), default=str)
        }
        
        # Enregistrer dans DynamoDB
        table.put_item(Item=item)
        
        logger.info(f"Callback enregistré pour task_id: {task_id}, batch_id: {batch_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Callback reçu et enregistré',
                'task_id': task_id,
                'batch_id': batch_id,
                'timestamp': timestamp
            }),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
        
    except Exception as e:
        logger.error(f"Erreur dans handle_callback_post: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Erreur lors de l\'enregistrement: {str(e)}'}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }


def handle_callback_get(event, context):
    """
    Récupère les résultats d'un callback spécifique
    """
    try:
        task_id = event['pathParameters']['task_id']
        
        # Récupérer l'item de DynamoDB
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('task_id').eq(task_id),
            ScanIndexForward=False,  # Tri par timestamp décroissant
            Limit=10  # Limiter à 10 résultats
        )
        
        items = response.get('Items', [])
        
        # Convertir les résultats pour la réponse JSON
        results = []
        for item in items:
            # Convertir processing_time de Decimal en float pour JSON
            processing_time = item.get('processing_time', 0)
            if isinstance(processing_time, Decimal):
                processing_time = float(processing_time)
            
            result = {
                'task_id': item['task_id'],
                'timestamp': item['timestamp'],
                'status': item['status'],
                'file_url': item['file_url'],
                'analysis_results': json.loads(item.get('analysis_results', '{}')),
                'error_message': item.get('error_message', ''),
                'processing_time': processing_time,
                'batch_id': item.get('batch_id', str(uuid.uuid4())),
                'metadata': json.loads(item.get('metadata', '{}'))
            }
            results.append(result)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'task_id': task_id,
                'results': results,
                'count': len(results)
            }),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
        
    except Exception as e:
        logger.error(f"Erreur dans handle_callback_get: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Erreur lors de la récupération: {str(e)}'}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }


def handle_batch_get(event, context):
    """
    Récupère tous les résultats d'un batch
    """
    try:
        batch_id = event['pathParameters']['batch_id']
        
        # Requête sur l'index secondaire global
        response = table.query(
            IndexName=batch_index_name,
            KeyConditionExpression=boto3.dynamodb.conditions.Key('batch_id').eq(batch_id),
            ScanIndexForward=False  # Tri par timestamp décroissant
        )
        
        items = response.get('Items', [])
        
        # Convertir les résultats
        results = []
        for item in items:
            # Convertir processing_time de Decimal en float pour JSON
            processing_time = item.get('processing_time', 0)
            if isinstance(processing_time, Decimal):
                processing_time = float(processing_time)
            
            result = {
                'task_id': item['task_id'],
                'timestamp': item['timestamp'],
                'status': item['status'],
                'file_url': item['file_url'],
                'analysis_results': json.loads(item.get('analysis_results', '{}')),
                'error_message': item.get('error_message', ''),
                'processing_time': processing_time,
                'batch_id': item.get('batch_id', str(uuid.uuid4())),
                'metadata': json.loads(item.get('metadata', '{}'))
            }
            results.append(result)
        
        # Calculer des statistiques du batch
        stats = {
            'total_tasks': len(results),
            'completed': len([r for r in results if r['status'] == 'completed']),
            'failed': len([r for r in results if r['status'] == 'failed']),
            'processing': len([r for r in results if r['status'] == 'processing'])
        }
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'batch_id': batch_id,
                'results': results,
                'statistics': stats
            }),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
        
    except Exception as e:
        logger.error(f"Erreur dans handle_batch_get: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Erreur lors de la récupération du batch: {str(e)}'}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
