import json
import boto3
import os
import subprocess
import tempfile
import urllib.request
import logging
import uuid
import re
from datetime import datetime
import requests

# Configuration du logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Chemins vers les binaires ffmpeg (depuis notre Layer Lambda)
FFMPEG_PATH = '/opt/bin/ffmpeg'
FFPROBE_PATH = '/opt/bin/ffprobe'

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
    Handler principal pour l'analyse MP4
    """
    try:
        # Parser le body de la requête
        if event.get('body'):
            request_data = json.loads(event['body'])
        else:
            return json_response({'error': 'Body de requête manquant'}, 400)
        
        # Valider les paramètres requis
        file_url = request_data.get('file_url')
        callback_url = request_data.get('callback_url')
        
        if not file_url:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'file_url est requis'
                }),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
        
        # callback_url est optionnel (mode synchrone vs asynchrone)
        
        # Auto-générer task_id s'il n'est pas fourni
        task_id = request_data.get('task_id')
        if not task_id or not task_id.strip():
            task_id = str(uuid.uuid4())
        
        # Récupérer la méthode HTTP pour le callback (POST par défaut)
        callback_method = request_data.get('method', 'POST').upper()
        if callback_method not in ['POST', 'PUT']:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'La méthode doit être POST ou PUT'
                }),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
        
        # Analyser le fichier MP4
        logger.info(f"Début de l'analyse pour task_id: {task_id}, URL: {file_url}")
        start_time = datetime.now()
        
        analysis_result = analyze_mp4_from_url(file_url)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Préparer les données de callback/réponse
        callback_data = {
            'status': 'completed',
            'results': analysis_result,
            'task_id': task_id,
            'processing_time': round(processing_time, 2),
            'metadata': {
                'task_id': task_id,
                'source_url': file_url,
                'processor': 'mp4_small_analyser',
                'version': '1.0.0',
                'processed_at': end_time.isoformat()
            }
        }
        
        # Mode asynchrone : envoyer le callback
        if callback_url:
            send_callback(callback_url, task_id, callback_data, callback_method)
            logger.info(f"Analyse terminée pour task_id: {task_id} en {processing_time:.2f}s - Callback envoyé")
            
            return json_response({
                'message': 'Analyse lancée avec succès',
                'task_id': task_id,
                'callback_url': callback_url,
                'processing_time': round(processing_time, 2)
            })
        else:
            # Mode synchrone : retourner directement les résultats
            logger.info(f"Analyse terminée pour task_id: {task_id} en {processing_time:.2f}s - Mode synchrone")
            
            return json_response({
                'message': 'Analyse terminée avec succès',
                'task_id': task_id,
                'results': analysis_result,
                'status': 'completed',
                'processing_time': round(processing_time, 2)
            })
        
    except Exception as e:
        logger.error(f"Erreur dans lambda_handler: {str(e)}")
        
        # Essayer d'envoyer un callback d'erreur si possible
        try:
            # Calculer le temps de traitement même en cas d'erreur
            if 'start_time' in locals():
                processing_time = (datetime.now() - start_time).total_seconds()
            else:
                processing_time = 0
            
            # Utiliser les variables déjà définies ou des valeurs par défaut
            if 'callback_url' not in locals():
                callback_url = request_data.get('callback_url') if 'request_data' in locals() else None
            if 'task_id' not in locals():
                task_id = request_data.get('task_id') if 'request_data' in locals() else str(uuid.uuid4())
            
            error_callback = {
                'status': 'failed',
                'error': str(e),
                'task_id': task_id,
                'processing_time': round(processing_time, 2),
                'metadata': {
                    'task_id': task_id,
                    'processor': 'mp4_small_analyser',
                    'failed_at': datetime.now().isoformat()
                }
            }
            
            if callback_url:
                # Mode asynchrone : envoyer le callback d'erreur
                send_callback(callback_url, task_id, error_callback, 'POST')
                return json_response({'error': f'Erreur lors de l\'analyse: {str(e)}'}, 500)
            else:
                # Mode synchrone : retourner l'erreur directement avec les détails
                return json_response({
                    'error': f'Erreur lors de l\'analyse: {str(e)}',
                    'task_id': task_id,
                    'status': 'failed',
                    'processing_time': round(processing_time, 2)
                }, 500)
        except:
            pass
        
        return json_response({'error': f'Erreur lors de l\'analyse: {str(e)}'}, 500)


def download_mp4(url):
    """Télécharge un fichier MP4 depuis une URL"""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    logger.info(f"Téléchargement du fichier depuis {url}...")
    
    # urllib.request.urlopen suit automatiquement les redirections (max 30)
    try:
        with urllib.request.urlopen(url) as response:
            tmp.write(response.read())
        tmp.close()
        return tmp.name
    except Exception as e:
        tmp.close()
        if os.path.exists(tmp.name):
            os.remove(tmp.name)
        raise


def run_cmd(cmd):
    """Exécute une commande système"""
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.stdout + result.stderr


def get_durations(file_path):
    """Récupère les durées audio et vidéo"""
    cmd = [
        FFPROBE_PATH, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        file_path
    ]
    output = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    duration = float(json.loads(output.stdout)["format"]["duration"])
    return round(duration, 2), round(duration, 2)  # audioDuration, videoDuration


def has_audio_stream(file_path):
    """Vérifie si le fichier a une piste audio"""
    cmd = [
        FFPROBE_PATH, "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_type",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, text=True).stdout.strip()
    return result == "audio"


def get_loudness(file_path):
    """Analyse la loudness du fichier audio"""
    cmd = [
        FFMPEG_PATH, "-hide_banner", "-nostats", "-i", file_path,
        "-filter_complex", "ebur128=peak=true",
        "-f", "null", "-"
    ]
    output = run_cmd(cmd)

    measured = None
    true_peak = None
    
    # Rechercher d'abord dans le résumé final (Summary section)
    summary_section = False
    for line in output.splitlines():
        if "Summary:" in line:
            summary_section = True
            continue
            
        if summary_section:
            # Dans la section Summary, chercher la loudness intégrée
            if "I:" in line and "LUFS" in line and measured is None:
                match = re.search(r"I:\s*(-?\d+\.\d+)\s*LUFS", line)
                if match:
                    measured = float(match.group(1))
            
            # Dans la section Summary, chercher le true peak
            elif "Peak:" in line and "dBFS" in line and true_peak is None:
                match = re.search(r"Peak:\s*(-?\d+\.\d+)\s*dBFS", line)
                if match:
                    true_peak = float(match.group(1))
    
    # Si pas trouvé dans le résumé, chercher dans les lignes de progression
    if measured is None or true_peak is None:
        for line in output.splitlines():
            # Recherche dans les lignes de progression pour la loudness
            if "I:" in line and "LUFS" in line and measured is None:
                match = re.search(r"I:\s*(-?\d+\.\d+)\s*LUFS", line)
                if match:
                    measured = float(match.group(1))
            
            # Recherche du true peak dans les lignes TPK
            if "TPK:" in line and true_peak is None:
                # Extraire la première valeur TPK (canal gauche)
                match = re.search(r"TPK:\s*(-?\d+\.\d+)", line)
                if match:
                    true_peak = float(match.group(1))

    # Si on n'arrive toujours pas à extraire les valeurs, retourner des valeurs par défaut
    if measured is None:
        logger.warning("Impossible d'extraire la loudness intégrée, utilisation de -23.0 LUFS par défaut")
        measured = -23.0
    
    if true_peak is None:
        logger.warning("Impossible d'extraire le true peak, utilisation de -1.0 dBFS par défaut")
        true_peak = -1.0

    return measured, true_peak


def get_silence_percentage(file_path, duration):
    """Calcule le pourcentage de silence"""
    cmd = [
        FFMPEG_PATH, "-i", file_path,
        "-af", "silencedetect=n=-50dB:d=0.5",
        "-f", "null", "-"
    ]
    output = run_cmd(cmd)

    silence_durations = []
    silence_start = None
    for line in output.splitlines():
        if "silence_start" in line:
            match = re.search(r"silence_start: (\d+(\.\d+)?)", line)
            if match:
                silence_start = float(match.group(1))
        elif "silence_end" in line and silence_start is not None:
            match = re.search(r"silence_end: (\d+(\.\d+)?)", line)
            if match:
                silence_end = float(match.group(1))
                silence_durations.append(silence_end - silence_start)
                silence_start = None

    silence_total = sum(silence_durations)
    return round((silence_total / duration) * 100, 2)


def analyze_mp4_from_url(file_url):
    """Analyse complète d'un fichier MP4 depuis une URL"""
    start_time = datetime.now()
    local_path = None
    
    try:
        # Télécharger le fichier
        local_path = download_mp4(file_url)
        
        # Vérifier qu'il y a une piste audio
        if not has_audio_stream(local_path):
            raise ValueError("Le fichier ne contient pas de piste audio.")
        
        # Analyse complète
        audio_duration, video_duration = get_durations(local_path)
        loudness_measured, loudness_true_peak = get_loudness(local_path)
        silence_percentage = get_silence_percentage(local_path, audio_duration)
        
        # Calculer le temps de traitement
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "silencePercentage": silence_percentage,
            "loudnessMeasured": loudness_measured,
            "loudnessTruePeak": loudness_true_peak,
            "audioDuration": audio_duration,
            "videoDuration": video_duration,
            "processing_time": round(processing_time, 2)
        }
        
    finally:
        # Nettoyer le fichier temporaire
        if local_path and os.path.exists(local_path):
            os.remove(local_path)


def send_callback(callback_url, task_id, callback_data, method='POST'):
    """Envoie le callback au système demandeur"""
    try:
        # Utiliser directement l'URL de callback fournie (elle contient déjà le task_id si nécessaire)
        full_callback_url = callback_url.rstrip('/')
        
        # Choisir la méthode HTTP appropriée
        method = method.upper()
        if method == 'PUT':
            response = requests.put(
                full_callback_url,
                json=callback_data,
                allow_redirects=True,
                headers={'Content-Type': 'application/json'}
            )
        else:  # POST par défaut
            response = requests.post(
                full_callback_url,
                json=callback_data,
                allow_redirects=True,
                headers={'Content-Type': 'application/json'}
            )
        
        # Lever une exception pour les codes d'erreur HTTP
        response.raise_for_status()
        
        logger.info(f"Callback {method} envoyé avec succès pour {task_id} (status: {response.status_code})")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur de requête lors de l'envoi du callback {method} pour {task_id}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du callback {method} pour {task_id}: {str(e)}")
        raise
