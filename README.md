# MP4 Small Analyser CDK

Une solution serverless complète pour l'analyse de fichiers MP4 déployée sur AWS avec CDK. Le système prend en charge l'analyse synchrone et asynchrone de fichiers MP4 avec callback automatique.

## 🔗 Repository

**GitHub**: [https://github.com/Hapsout/mp4-small-analyser-cdk](https://github.com/Hapsout/mp4-small-analyser-cdk)

## 📋 Prérequis

- **AWS CLI** configuré avec les bonnes permissions
- **Node.js** et npm (pour AWS CDK CLI)
- **Python 3.12+** et pip
- **Git** pour cloner le repository

## 🚀 Installation et Configuration

### 1. Cloner le repository

```bash
git clone git@github.com:Hapsout/mp4-small-analyser-cdk.git
cd mp4-small-analyser-cdk
```

### 2. Configuration

Créez votre fichier de configuration `.env` :

```bash
cp .env.example .env
# Éditez le fichier .env avec vos paramètres AWS
```

### 3. Installation des dépendances

```bash
# Créer et activer l'environnement virtuel Python
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS

# Installer les dépendances
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Déploiement

```bash
# Bootstrap CDK (première fois uniquement)
./cdk.sh bootstrap

# Déployer l'infrastructure complète
./cdk.sh deploy --all
```

Après le déploiement, les URLs d'API sont sauvegardées dans `urls.txt`.

## 🏗️ Architecture

### Composants Principaux

1. **Mp4SmallAnalyserCdkStack** : Stack principale avec :

   - **API Gateway** : Endpoint unifié `/mp4_small_analyser`
   - **Lambda Dispatcher** : Gère le routage synchrone/asynchrone
   - **Lambda MP4 Analyser** : Analyse les fichiers MP4 avec ffmpeg

2. **Mp4AnalyserCallbackStack** : Stack de callback avec :
   - **API Gateway** : Endpoints de callback et récupération
   - **Lambda Callback** : Traitement et stockage des résultats
   - **DynamoDB** : Stockage des résultats d'analyse

### Flux de Traitement

```
Client Request → Dispatcher → MP4 Analyser → Callback (si async) → DynamoDB
              ↓
         Response (si sync)
```

## 🔧 Utilisation de l'API

### Endpoint Principal

**URL** : `https://{api-id}.execute-api.{region}.amazonaws.com/prod/mp4_small_analyser`

### Mode Synchrone

Pour une analyse immédiate avec réponse directe :

```bash
curl -X POST "https://your-api-url/prod/mp4_small_analyser" \
  -H "Content-Type: application/json" \
  -d '{
    "files_url": [
        "https://example.com/video.mp4",
        "https://example.com/video_2.mp4"
    ]
  }'
```

**Réponse synchrone :**

```json
{
  "message": "3 analyses terminées avec succès en mode synchrone",
  "mode": "sync",
  "total_files": 3,
  "dispatcher_processing_time": 2.45,
  "results": [
    {
      "task_id": "abc123",
      "file_url": "https://example.com/video.mp4",
      "status": "completed",
      "processing_time": 1.23,
      "results": {
        "silencePercentage": 15.5,
        "loudnessMeasured": -18.2,
        "loudnessTruePeak": -3.1,
        "audioDuration": 30.5,
        "videoDuration": 30.5
      }
    }
  ]
}
```

### Mode Asynchrone

Pour traiter plusieurs fichiers en parallèle avec callback :

```bash
curl -X POST "https://your-api-url/prod/mp4_small_analyser" \
  -H "Content-Type: application/json" \
  -d '{
    "files_url": [
        "file_url": "https://example.com/video1.mp4",
        "file_url": "https://example.com/video2.mp4"
        ],
    "callback_url": "https://callback-api-url/prod/callback"
  }'
```

**Réponse asynchrone :**

```json
{
  "message": "2 analyses lancées avec succès en mode asynchrone",
  "mode": "async",
  "total_files": 2,
  "dispatcher_processing_time": 0.15,
  "tasks": [
    {
      "task_id": "def456",
      "file_url": "https://example.com/video1.mp4",
      "callback_url": "https://callback-api-url/prod/callback/997c76c4-ae68-4547-a0e8-cbf8c5fc0128",
      "status": "launched"
    }
  ]
}
```

### Récupération des Résultats

Une fois l'analyse terminée (mode asynchrone), récupérez les résultats :

````bash
# Résultat d'une tâche spécifique
curl "https://callback-api-url/prod/callback/{task_id}"


## 📄 Format des Résultats

### Analyse Réussie

```json
{
  "status": "completed",
  "task_id": "abc123",
  "processing_time": 1.23,
  "results": {
    "silencePercentage": 15.5,
    "loudnessMeasured": -18.2,
    "loudnessTruePeak": -3.1,
    "audioDuration": 30.5,
    "videoDuration": 30.5,
    "processing_time": 1.15
  },
  "metadata": {
    "task_id": "abc123",
    "source_url": "https://example.com/video.mp4",
    "processor": "mp4_small_analyser",
    "version": "1.0.0",
    "processed_at": "2025-08-04T15:30:45.123456"
  }
}
````

### Analyse Échouée

```json
{
  "status": "failed",
  "task_id": "def456",
  "processing_time": 0.5,
  "error": "Le fichier ne contient pas de piste audio.",
  "metadata": {
    "task_id": "def456",
    "processor": "mp4_small_analyser",
    "failed_at": "2025-08-04T15:30:45.123456"
  }
}
```

## 📊 Métriques d'Analyse

Le système fournit plusieurs métriques audio :

- **silencePercentage** : Pourcentage de silence dans l'audio (seuil : -50dB, durée min : 0.5s)
- **loudnessMeasured** : Loudness intégrée en LUFS (EBU R128)
- **loudnessTruePeak** : True peak en dBFS
- **audioDuration** : Durée de la piste audio en secondes
- **videoDuration** : Durée de la piste vidéo en secondes
- **processing_time** : Temps de traitement individuel du fichier

## 🧪 Exemples et Tests

Le repository inclut plusieurs fichiers d'exemple :

- `new_sync_request_example.json` : Requête synchrone
- `new_async_request_example.json` : Requête asynchrone
- `exemples/` : Dossier avec différents formats de requêtes

### Test Rapide

```bash
# Test synchrone avec un fichier court
curl -X POST "$(cat urls.txt | grep 'MP4 Analyser' | cut -d' ' -f4)" \
  -H "Content-Type: application/json" \
  -d @new_sync_request_example.json
```

## 🔧 Configuration

### Configuration Interactive

Pour une configuration guidée, utilisez le script fourni :

```bash
./setup-config.sh
```

Ce script vous aide à :

- ✅ Auto-détecter votre ID de compte AWS
- ✅ Configurer la région AWS (défaut: eu-west-1)
- ✅ Définir le profil AWS à utiliser
- ✅ Personnaliser le nom du projet et l'environnement
- ✅ Générer automatiquement le fichier `.env`

### Variables d'Environnement (.env)

Si vous préférez configurer manuellement :

```bash
# Configuration AWS
AWS_ACCOUNT_ID=123456789012
AWS_REGION=eu-west-1
AWS_PROFILE=default

# Configuration du projet
PROJECT_NAME=mp4-small-analyser
ENVIRONMENT=dev
```

### Limites et Timeouts

- **Lambda Timeout** : 2 minutes pour l'analyser, 30s pour le dispatcher
- **Lambda Memory** : 2048MB pour l'analyser (ffmpeg), 512MB pour le dispatcher
- **Concurrence** : Jusqu'à 1000 exécutions Lambda simultanées
- **Taille fichier** : Limitée par la mémoire Lambda et le timeout

## 🔐 Sécurité et Permissions

- ✅ CORS configuré pour tous les origins (`*`)
- ✅ Permissions IAM minimales pour chaque Lambda
- ✅ Chiffrement au repos avec DynamoDB
- ✅ Variables d'environnement sécurisées
- ✅ Logs CloudWatch automatiques

## 📊 Monitoring et Logs

### CloudWatch Logs

```bash
# Logs du dispatcher
aws logs tail "/aws/lambda/Mp4-small-analyserCdkStac-MP4DispatcherFunction75B-xxxxx" --follow

# Logs de l'analyser
aws logs tail "/aws/lambda/Mp4-small-analyserCdkStac-MP4AnalyserFunctionEC0C4-xxxxx" --follow

# Logs du callback
aws logs tail "/aws/lambda/Mp4-small-analyserCallback-CallbackHandler4434C38D-xxxxx" --follow
```

### Métriques

- **API Gateway** : Latence, erreurs, nombre de requêtes
- **Lambda** : Durée d'exécution, erreurs, invocations
- **DynamoDB** : Lectures/écritures, throttling

## 🚀 Déploiement en Production

### Checklist Pré-Production

- [ ] Tester avec différents formats de fichiers MP4
- [ ] Vérifier les limites de timeout pour les gros fichiers
- [ ] Configurer les alertes CloudWatch
- [ ] Tester la montée en charge
- [ ] Sauvegarder la configuration DynamoDB

### Scaling

Le système scale automatiquement :

- **Lambda** : Concurrence automatique jusqu'à 1000
- **API Gateway** : 10,000 requêtes/seconde par défaut
- **DynamoDB** : Mode pay-per-request (scaling automatique)

## 🆘 Dépannage

### Erreurs Communes

```bash
# "Body de requête manquant"
→ Vérifier le Content-Type: application/json

# "file_url est requis"
→ Vérifier la structure JSON avec le champ files[]

# Timeout Lambda
→ Fichier trop volumineux ou URL lente, réduire la taille

# "Le fichier ne contient pas de piste audio"
→ Fichier vidéo sans piste audio, vérifier le contenu
```

### Debug

```bash
# Vérifier le statut des stacks
./cdk.sh list

# Voir les différences avant déploiement
./cdk.sh diff

# Récupérer les URLs après déploiement
cat urls.txt
```

## 🔄 Maintenance

### Mise à Jour

```bash
# Mettre à jour le code
git pull
./cdk.sh deploy --all
```

### Nettoyage

```bash
# Supprimer l'infrastructure
./cdk.sh destroy --all

# Nettoyer l'environnement local
rm -rf .venv cdk.out urls.txt
```

---
