import json
import boto3
import logging
import uuid
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

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
    Handler pour lancer une ou plusieurs analyses MP4
    Supporte deux formats :
    1. Avec callback_url : mode asynchrone (lance et retourne immédiatement)
    2. Sans callback_url : mode synchrone (attend toutes les réponses)
    """
    start_time = datetime.now()
    
    try:
        # Parser le body de la requête
        if event.get('body'):
            request_data = json.loads(event['body'])
        else:
            return json_response({'error': 'Body de requête manquant'}, 400)
        
        # Valider que files_url est présent
        files_url = request_data.get('files_url', [])
        if not files_url:
            return json_response({'error': 'files_url est requis et doit contenir au moins une URL'}, 400)
        
        callback_url = request_data.get('callback_url')
        
        if callback_url:
            # Mode asynchrone : lancer les analyses et retourner immédiatement
            return handle_async_mode(files_url, callback_url, start_time)
        else:
            # Mode synchrone : attendre toutes les réponses
            return handle_sync_mode(files_url, start_time)
            
    except Exception as e:
        logger.error(f"Erreur dans lambda_handler: {str(e)}")
        return json_response({'error': f'Erreur lors du lancement de l\'analyse: {str(e)}'}, 500)


def handle_async_mode(files_url, callback_url, start_time):
    """
    Mode asynchrone : lance les analyses et retourne immédiatement
    Les résultats seront envoyés aux URLs de callback individuelles
    """
    try:
        mp4_lambda_name = os.environ.get('MP4_LAMBDA_NAME')
        if not mp4_lambda_name:
            raise ValueError("MP4_LAMBDA_NAME non configuré dans les variables d'environnement")
        
        launched_tasks = []
        
        for file_url in files_url:
            # Générer un UUID unique pour chaque fichier
            file_uuid = str(uuid.uuid4())
            
            # Construire l'URL de callback avec l'UUID
            individual_callback_url = f"{callback_url.rstrip('/')}/{file_uuid}"
            
            # Préparer les données pour la lambda MP4 analyser
            task_data = {
                'file_url': file_url,
                'callback_url': individual_callback_url,
                'task_id': file_uuid
            }
            
            # Préparer le payload comme si c'était une requête API Gateway
            payload = {
                'httpMethod': 'POST',
                'body': json.dumps(task_data),
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
            
            if response['StatusCode'] == 202:
                launched_tasks.append({
                    'file_url': file_url,
                    'task_id': file_uuid,
                    'callback_url': individual_callback_url,
                    'status': 'launched'
                })
                logger.info(f"Analyse MP4 lancée avec succès pour {file_url} avec task_id: {file_uuid}")
            else:
                logger.error(f"Erreur lors de l'invocation Lambda pour {file_url}: status {response['StatusCode']}")
                launched_tasks.append({
                    'file_url': file_url,
                    'task_id': file_uuid,
                    'callback_url': individual_callback_url,
                    'status': 'error',
                    'error': f"Erreur d'invocation Lambda: status {response['StatusCode']}"
                })
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return json_response({
            'message': f'{len(launched_tasks)} analyses lancées avec succès en mode asynchrone',
            'mode': 'async',
            'total_files': len(files_url),
            'dispatcher_processing_time': round(processing_time, 2),
            'tasks': launched_tasks
        }, 202)
        
    except Exception as e:
        logger.error(f"Erreur dans handle_async_mode: {str(e)}")
        return json_response({'error': f'Erreur en mode asynchrone: {str(e)}'}, 500)


def handle_sync_mode(files_url, start_time):
    """
    Mode synchrone : lance les analyses en parallèle et attend toutes les réponses
    """
    try:
        mp4_lambda_name = os.environ.get('MP4_LAMBDA_NAME')
        if not mp4_lambda_name:
            raise ValueError("MP4_LAMBDA_NAME non configuré dans les variables d'environnement")
        
        results = []
        
        # Utiliser ThreadPoolExecutor pour lancer les invocations Lambda en parallèle
        with ThreadPoolExecutor(max_workers=10) as executor:  # Limiter à 10 tâches simultanées
            # Préparer les tâches
            future_to_file = {}
            
            for file_url in files_url:
                # Générer un UUID unique pour chaque fichier
                file_uuid = str(uuid.uuid4())
                
                # Soumettre la tâche
                future = executor.submit(invoke_mp4_lambda_sync, mp4_lambda_name, file_url, file_uuid)
                future_to_file[future] = {'file_url': file_url, 'task_id': file_uuid}
            
            # Collecter les résultats
            for future in future_to_file:
                file_info = future_to_file[future]
                try:
                    result = future.result()
                    results.append({
                        'file_url': file_info['file_url'],
                        'task_id': file_info['task_id'],
                        'success': result['success'],
                        'analysis_result': result.get('analysis_result'),
                        'error': result.get('error')
                    })
                except Exception as e:
                    logger.error(f"Erreur lors du traitement de {file_info['file_url']}: {str(e)}")
                    results.append({
                        'file_url': file_info['file_url'],
                        'task_id': file_info['task_id'],
                        'success': False,
                        'error': str(e)
                    })
        
        # Compter les succès et échecs
        successful = len([r for r in results if r['success']])
        failed = len([r for r in results if not r['success']])
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return json_response({
            'message': f'Traitement synchrone terminé: {successful} succès, {failed} échecs',
            'mode': 'sync',
            'total_files': len(files_url),
            'successful': successful,
            'failed': failed,
            'dispatcher_processing_time': round(processing_time, 2),
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Erreur dans handle_sync_mode: {str(e)}")
        return json_response({'error': f'Erreur en mode synchrone: {str(e)}'}, 500)


def invoke_mp4_lambda_sync(lambda_name, file_url, task_id):
    """
    Invoque la Lambda MP4 analyser de manière synchrone et récupère le résultat
    """
    try:
        # Préparer les données pour la lambda MP4 analyser
        task_data = {
            'file_url': file_url,
            'task_id': task_id
            # Pas de callback_url en mode synchrone
        }
        
        # Préparer le payload comme si c'était une requête API Gateway
        payload = {
            'httpMethod': 'POST',
            'body': json.dumps(task_data),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
        
        # Invoquer la Lambda de manière synchrone
        response = lambda_client.invoke(
            FunctionName=lambda_name,
            InvocationType='RequestResponse',  # Synchrone
            Payload=json.dumps(payload)
        )
        
        # Lire la réponse
        response_payload = json.loads(response['Payload'].read())
        
        if response['StatusCode'] == 200:
            # Parser la réponse de la lambda MP4
            if response_payload.get('statusCode') == 200:
                body = json.loads(response_payload.get('body', '{}'))
                logger.info(f"Lambda MP4 exécutée avec succès pour {file_url}")
                return {
                    'success': True,
                    'analysis_result': body
                }
            else:
                error_body = json.loads(response_payload.get('body', '{}'))
                logger.error(f"Erreur dans la lambda MP4 pour {file_url}: {error_body}")
                return {
                    'success': False,
                    'error': error_body.get('error', 'Erreur inconnue dans la lambda MP4')
                }
        else:
            logger.error(f"Erreur lors de l'invocation Lambda pour {file_url}: status {response['StatusCode']}")
            return {
                'success': False,
                'error': f"Erreur d'invocation Lambda: status {response['StatusCode']}"
            }
            
    except Exception as e:
        logger.error(f"Erreur lors de l'invocation de la Lambda MP4 pour {file_url}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
