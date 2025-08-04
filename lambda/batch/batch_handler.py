import json
import boto3
import logging
import uuid
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import threading

# Configuration du logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Client Lambda
lambda_client = boto3.client('lambda')

def json_response(data, status_code=200):
    """Utilitaire pour créer des réponses JSON avec caractères accentués lisibles"""
    return {
        'statusCode': status_code,
        'body': json.dumps(data, ensure_ascii=False, indent=2),
        'headers': {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
        }
    }

def lambda_handler(event, context):
    """
    Handler pour le traitement en batch des analyses MP4
    """
    try:
        # Parser le body de la requête
        if event.get('body'):
            batch_data = json.loads(event['body'])
        else:
            return json_response({'error': 'Body de requête manquant'}, 400)
        
        # Valider la structure du batch
        mp4_tasks = batch_data.get('mp4_small_analyser', [])
        metadata = batch_data.get('metadata', {})
        
        if not mp4_tasks:
            return json_response({
                'error': 'Aucune tâche mp4_small_analyser trouvée dans le batch'
            }, 400)
        
        # Générer un batch_id unique si pas fourni
        batch_id = metadata.get('batch_id')
        if not batch_id or not batch_id.strip():
            batch_id = str(uuid.uuid4())
        
        logger.info(f"Traitement du batch {batch_id} avec {len(mp4_tasks)} tâches")
        
        # Récupérer le nom de la Lambda MP4 analyser depuis les variables d'environnement
        mp4_lambda_name = os.environ.get('MP4_LAMBDA_NAME')
        if not mp4_lambda_name:
            raise ValueError("MP4_LAMBDA_NAME non configuré dans les variables d'environnement")
        
        # Lancer les analyses en parallèle
        results = launch_parallel_analyses(mp4_lambda_name, mp4_tasks, batch_id)
        
        # Compter les succès et échecs
        successful = len([r for r in results if r['success']])
        failed = len([r for r in results if not r['success']])
        
        logger.info(f"Batch {batch_id} terminé: {successful} succès, {failed} échecs")
        
        return json_response({
            'message': 'Batch traité avec succès',
            'batch_id': batch_id,
            'total_tasks': len(mp4_tasks),
            'successful': successful,
            'failed': failed,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Erreur dans lambda_handler: {str(e)}")
        return json_response({'error': f'Erreur lors du traitement du batch: {str(e)}'}, 500)


def launch_parallel_analyses(lambda_name, tasks, batch_id):
    """
    Lance les analyses MP4 en parallèle via des invocations Lambda
    """
    results = []
    
    # Utiliser ThreadPoolExecutor pour lancer les invocations Lambda en parallèle
    with ThreadPoolExecutor(max_workers=10) as executor:  # Limiter à 10 tâches simultanées
        # Préparer les tâches
        future_to_task = {}
        
        for i, task in enumerate(tasks):
            # Générer un task_id unique si pas fourni
            task_id = task.get('task_id')
            if not task_id or not task_id.strip():
                task_id = str(uuid.uuid4())
            
            # Ajouter batch_id, task_id et task_index aux métadonnées
            task_with_metadata = {
                **task,
                'batch_id': batch_id,
                'task_id': task_id,
                'task_index': i
            }
            
            # Soumettre la tâche
            future = executor.submit(invoke_mp4_lambda, lambda_name, task_with_metadata)
            future_to_task[future] = task_with_metadata
        
        # Collecter les résultats
        for future in future_to_task:
            task = future_to_task[future]
            try:
                result = future.result()
                results.append({
                    'task_index': task['task_index'],
                    'task_id': task['task_id'],
                    'file_url': task['file_url'], 
                    'callback_url': task['callback_url'],
                    'success': result['success'],
                    'message': result.get('message', ''),
                    'error': result.get('error', '')
                })
            except Exception as e:
                logger.error(f"Erreur lors du traitement de la tâche {task['task_index']}: {str(e)}")
                results.append({
                    'task_index': task['task_index'],
                    'task_id': task['task_id'],
                    'file_url': task['file_url'],
                    'callback_url': task['callback_url'],
                    'success': False,
                    'error': str(e)
                })
    
    return results


def invoke_mp4_lambda(lambda_name, task_data):
    """
    Invoque la Lambda MP4 analyser de manière asynchrone
    """
    try:
        # Préparer le payload comme si c'était une requête API Gateway
        payload = {
            'httpMethod': 'POST',
            'body': json.dumps(task_data),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
        # Invoquer la Lambda de manière asynchrone
        response = lambda_client.invoke(
            FunctionName=lambda_name,
            InvocationType='Event',  # Asynchrone
            Payload=json.dumps(payload)
        )
        
        # Vérifier le status code de l'invocation
        if response['StatusCode'] == 202:  # Accepted pour invocation asynchrone
            logger.info(f"Lambda MP4 invoquée avec succès pour {task_data['file_url']}")
            return {
                'success': True,
                'message': 'Analyse lancée avec succès'
            }
        else:
            logger.error(f"Erreur lors de l'invocation Lambda: status {response['StatusCode']}")
            return {
                'success': False,
                'error': f"Erreur d'invocation Lambda: status {response['StatusCode']}"
            }
            
    except Exception as e:
        logger.error(f"Erreur lors de l'invocation de la Lambda MP4: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
