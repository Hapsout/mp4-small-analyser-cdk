# MP4 Small Analyser CDK

Ce projet AWS CDK déploie une infrastructure pour analyser de petits fichiers MP4. Il comprend une API de callback pour recevoir et traiter les résultats d'analyse.

## 🔗 Repository

**GitHub**: [https://github.com/Hapsout/mp4-small-analyser-cdk](https://github.com/Hapsout/mp4-small-analyser-cdk)

## 📋 Prérequis

- **AWS CLI** configuré avec les bonnes permissions
- **Node.js** et npm (pour AWS CDK CLI)
- **Python 3.11+** et pip
- **Git** pour cloner le repository

## 🚀 Installation et Configuration

### 1. Cloner le repository

```bash
git clone git@github.com:Hapsout/mp4-small-analyser-cdk.git
cd mp4-small-analyser-cdk
```

### 2. Configuration interactive

Utilisez le script de configuration pour générer votre fichier `.env` :

```bash
./setup-config.sh
```

Ce script vous demande :

- **ID de compte AWS** (auto-détecté si possible)
- **Région AWS** (par défaut: eu-west-1)
- **Profil AWS** (par défaut: default)
- **Nom du projet** et **environnement**
- **Configuration avancée** (optionnelle)

### 3. Installation des dépendances

```bash
# Créer et activer l'environnement virtuel Python
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate.bat  # Windows

# Installer les dépendances
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 4. Bootstrap CDK (première fois uniquement)

```bash
# Avec le script configuré
./cdk-with-config.sh bootstrap

# Ou manuellement avec votre profil
cdk bootstrap --profile your-profile
```

## 🏗️ Architecture

### Stacks Déployées

1. **Mp4SmallAnalyserCdkStack** : Stack principale (vide pour l'instant)
2. **Mp4AnalyserCallbackStack** : API de callback avec :
   - **API Gateway** : Endpoints REST pour recevoir les callbacks
   - **Lambda Functions** : Traitement des callbacks et fonctions de test
   - **DynamoDB** : Stockage des résultats d'analyse

### Structure du Projet

```
mp4-small-analyser-cdk/
├── mp4_small_analyser_cdk/           # Code CDK principal
│   ├── callback_stack.py             # Stack API callback
│   └── mp4_small_analyser_cdk_stack.py
├── lambda/                           # Code des fonctions Lambda
│   ├── callback/                     # Handler pour callbacks
│   └── test/                         # Fonctions de test
├── tests/                            # Tests unitaires
├── *.json                           # Exemples de payloads
├── .env.example                     # Exemple de configuration
├── setup-config.sh                 # Script de configuration
├── cdk-with-config.sh              # Script CDK avec config
└── app.py                          # Point d'entrée CDK
```

## 🔧 Utilisation

### Commandes de Déploiement

```bash
# Lister les stacks
./cdk-with-config.sh list

# Synthétiser les templates
./cdk-with-config.sh synth

# Voir les différences
./cdk-with-config.sh diff

# Déployer toutes les stacks
./cdk-with-config.sh deploy --all

# Déployer una stack spécifique
./cdk-with-config.sh deploy Mp4AnalyserCallbackStack

# Supprimer les stacks
./cdk-with-config.sh destroy --all
```

### API Callback Endpoints

Une fois déployée, l'API callback fournit les endpoints suivants :

#### 📤 Recevoir un Callback

```http
POST /callback/{task_id}
Content-Type: application/json

{
  "status": "completed",
  "task_id": "task-001",
  "batch_id": "batch-2025-08-04-001",
  "file_url": "https://example.com/video.mp4",
  "results": { ... },
  "metadata": { ... }
}
```

#### 📥 Récupérer les Résultats

```bash
# Résultats d'une tâche spécifique
GET /callback/{task_id}

# Tous les résultats d'un batch
GET /callback/batch/{batch_id}

# Lister tous les résultats (debug)
GET /test/results?limit=50
```

#### 🧪 Tests et Simulation

```bash
# Simuler un callback pour test
POST /test/simulate
{
  "task_id": "test-task-001",
  "status": "completed",
  "file_url": "https://example.com/test.mp4"
}
```

## 📄 Exemples de Payloads

### Callback de Succès

Voir `callback_payload_exemple.json` :

```json
{
  "status": "completed",
  "task_id": "task-001",
  "batch_id": "batch-2025-08-04-001",
  "file_url": "https://example.com/video.mp4",
  "processing_time": 15.23,
  "results": {
    "file_info": {
      "file_size": 2048576,
      "duration": 30.067,
      "format": "mp4"
    },
    "video_analysis": {
      "codec": "h264",
      "resolution": "1920x1080",
      "quality_score": 0.85
    },
    "audio_analysis": {
      "codec": "aac",
      "quality_score": 0.9
    }
  }
}
```

### Callback d'Erreur

Voir `callback_error_exemple.json` :

```json
{
  "status": "failed",
  "task_id": "task-002",
  "error": "Unable to download file: HTTP 404 Not Found",
  "error_code": "FILE_NOT_FOUND"
}
```

### Requête Batch

Voir `batch_request_exemple.json` pour le format de requête avec plusieurs commandes :

```json
{
  "mp4_small_analyser": [
    {
      "file_url": "https://example.com/video1.mp4",
      "callback_url": "https://your-api.com/callback/task-001"
    }
  ]
}
```

## 🧪 Tests et Développement

### Tests Unitaires

```bash
# Exécuter les tests
pytest

# Tests avec coverage
pytest --cov=mp4_small_analyser_cdk
```

### Tests d'Intégration API

```bash
# Obtenir l'URL de l'API après déploiement
./cdk-with-config.sh synth Mp4AnalyserCallbackStack | grep CallbackApiEndpoint

# Tester l'API
curl -X POST "https://your-api-id.execute-api.region.amazonaws.com/prod/test/simulate" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "test-001", "status": "completed"}'
```

### Variables d'Environnement

Le fichier `.env` (généré par `setup-config.sh`) :

```bash
# Configuration AWS
AWS_ACCOUNT_ID=123456789012
AWS_REGION=eu-west-1
AWS_PROFILE=default

# Configuration du projet
PROJECT_NAME=mp4-small-analyser
ENVIRONMENT=dev

# Tags de projet
CLIENT=nom-client
PROJECT=mp4-small-analyser

# Configuration des ressources
DYNAMODB_TABLE_NAME=mp4-analyser-callback-results
LAMBDA_TIMEOUT=30
LAMBDA_MEMORY_SIZE=256
```

## 🔐 Sécurité

- ✅ Le fichier `.env` est dans `.gitignore`
- ✅ CORS configuré pour l'API
- ✅ Permissions IAM minimales pour les Lambdas
- ✅ Chiffrement au repos avec DynamoDB
- ✅ Point-in-time recovery activé

## 🏷️ Tags et Organisation

Toutes les ressources AWS sont automatiquement taguées avec :

- **Environment** : Environnement de déploiement (dev/staging/prod)
- **Project** : Nom du projet
- **Client** : Nom du client
- **ManagedBy** : AWS-CDK
- **Owner** : MP4-Small-Analyser

Ces tags facilitent :

- 📊 La gestion des coûts par client/projet
- 🔍 Le filtrage des ressources dans la console AWS
- 📋 La génération de rapports de facturation
- 🔄 L'automatisation des processus DevOps

## 📊 Monitoring

### CloudWatch

- Logs des fonctions Lambda automatiquement créés
- Métriques API Gateway disponibles
- Métriques DynamoDB pour le suivi des performances

### DynamoDB

- **Table principale** : `{table-name}-{environment}`
- **Index secondaire** : `BatchIdIndex` pour requêtes par batch
- **Streams** : Activés pour traçabilité

## 🤝 Contribution

1. Créer une branche feature depuis `main`
2. Faire vos modifications et les tester
3. Soumettre une pull request

### Commandes de Développement

```bash
# Formater le code Python
black mp4_small_analyser_cdk/ lambda/

# Linter
flake8 mp4_small_analyser_cdk/ lambda/

# Type checking
mypy mp4_small_analyser_cdk/
```

## 📝 Notes Importantes

- **Environnements** : Le nom des ressources inclut l'environnement (`dev`, `staging`, `prod`)
- **Coûts** : DynamoDB en mode pay-per-request, Lambda facturé à l'usage
- **Limites** : Timeout Lambda par défaut 30s, mémoire 256MB
- **Régions** : Configuré pour fonctionner dans toutes les régions AWS

## 🆘 Dépannage

### Erreurs Communes

```bash
# Bootstrap manquant
Error: Need to perform AWS CDK bootstrap
→ Solution: ./cdk-with-config.sh bootstrap

# Permissions insuffisantes
Error: User is not authorized to perform action
→ Solution: Vérifier les permissions AWS du profil

# Configuration manquante
Error: File .env not found
→ Solution: Exécuter ./setup-config.sh
```

### Logs

```bash
# Logs des Lambdas
aws logs tail /aws/lambda/Mp4AnalyserCallbackStack-CallbackHandler --follow

# Logs API Gateway
aws logs tail /aws/apigateway/Mp4AnalyserCallbackStack --follow
```

---

Construit avec ❤️ en utilisant AWS CDK Python
