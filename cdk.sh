#!/bin/bash

# Script utilitaire pour charger la configuration et exécuter des commandes CDK
# Usage: ./cdk-with-config.sh [commande cdk]

CONFIG_FILE=".env"

# Vérifier si le fichier de config existe
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Fichier de configuration .env non trouvé."
    echo "💡 Exécutez './setup-config.sh' pour créer la configuration."
    exit 1
fi

# Charger la configuration
echo "📄 Chargement de la configuration depuis $CONFIG_FILE..."
set -a  # Exporter automatiquement toutes les variables
source "$CONFIG_FILE"
set +a

# Vérifier les variables essentielles
if [ -z "$AWS_ACCOUNT_ID" ] || [ -z "$AWS_REGION" ] || [ -z "$AWS_PROFILE" ]; then
    echo "❌ Configuration incomplète. Variables manquantes:"
    [ -z "$AWS_ACCOUNT_ID" ] && echo "  - AWS_ACCOUNT_ID"
    [ -z "$AWS_REGION" ] && echo "  - AWS_REGION"
    [ -z "$AWS_PROFILE" ] && echo "  - AWS_PROFILE"
    echo "💡 Exécutez './setup-config.sh' pour reconfigurer."
    exit 1
fi

# Afficher la configuration chargée
echo "✅ Configuration chargée:"
echo "  • Compte AWS: $AWS_ACCOUNT_ID"
echo "  • Région: $AWS_REGION"
echo "  • Profil: $AWS_PROFILE"
echo "  • Environnement: $ENVIRONMENT"
echo ""

# Activer l'environnement virtuel Python
if [ -d ".venv" ]; then
    echo "🐍 Activation de l'environnement virtuel Python..."
    source .venv/bin/activate
fi

# Construire la commande CDK avec les paramètres
CDK_CMD="cdk"
CDK_ARGS=""

# Ajouter le profil AWS
CDK_ARGS="$CDK_ARGS --profile $AWS_PROFILE"

# Ajouter le contexte de l'environnement
CDK_ARGS="$CDK_ARGS --context env=$ENVIRONMENT"

# Si aucune commande n'est fournie, afficher l'aide
if [ $# -eq 0 ]; then
    echo "🚀 Commandes disponibles:"
    echo "  • $0 list                    - Lister les stacks"
    echo "  • $0 synth                   - Synthétiser toutes les stacks"
    echo "  • $0 synth [stack-name]      - Synthétiser une stack spécifique"
    echo "  • $0 diff                    - Voir les différences"
    echo "  • $0 deploy --all            - Déployer toutes les stacks"
    echo "  • $0 deploy [stack-name]     - Déployer une stack spécifique"
    echo "  • $0 destroy --all           - Supprimer toutes les stacks"
    echo "  • $0 bootstrap               - Bootstrap de l'environnement CDK"
    echo ""
    echo "🔧 Configuration actuelle:"
    echo "  Commande: $CDK_CMD $CDK_ARGS [votre-commande]"
    exit 0
fi

# Exécuter la commande CDK avec les paramètres
echo "🔨 Exécution: $CDK_CMD $CDK_ARGS $*"
echo ""

# Vérifier si c'est une commande de déploiement
IS_DEPLOY=false
for arg in "$@"; do
    if [[ "$arg" == "deploy" ]]; then
        IS_DEPLOY=true
        break
    fi
done

# Exécuter la commande CDK
$CDK_CMD $CDK_ARGS "$@"
CDK_EXIT_CODE=$?

# Si le déploiement a réussi, générer le fichier urls.txt
if [ $IS_DEPLOY = true ] && [ $CDK_EXIT_CODE -eq 0 ]; then
    echo ""
    echo "🔍 Génération du fichier urls.txt..."
    
    # Récupérer les outputs des stacks
    MP4_API_URL=$(aws cloudformation describe-stacks \
        --stack-name Mp4-small-analyserCdkStack \
        --profile $AWS_PROFILE \
        --region $AWS_REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`MP4AnalyserApiUrl`].OutputValue' \
        --output text 2>/dev/null)

    CALLBACK_API_URL=$(aws cloudformation describe-stacks \
        --stack-name Mp4-small-analyserCallbackStack \
        --profile $AWS_PROFILE \
        --region $AWS_REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`CallbackApiUrl`].OutputValue' \
        --output text 2>/dev/null)

    # Générer le fichier urls.txt si les URLs sont disponibles
    if [ ! -z "$MP4_API_URL" ] && [ ! -z "$CALLBACK_API_URL" ]; then
        cat > urls.txt << EOF
# URLs des APIs MP4 Small Analyser
# Générées automatiquement le $(date)

# API principale pour l'analyse MP4
MP4_ANALYSER_URL=${MP4_API_URL}mp4_small_analyser

# API pour le traitement en batch  
BATCH_URL=${MP4_API_URL}batch

# API de callback pour recevoir les résultats
CALLBACK_URL=${CALLBACK_API_URL}callback

# URLs de test
# POST ${MP4_API_URL}mp4_small_analyser
# POST ${MP4_API_URL}batch
# POST ${CALLBACK_API_URL}callback/{task_id}
# GET  ${CALLBACK_API_URL}callback/{task_id}
# GET  ${CALLBACK_API_URL}callback/batch/{batch_id}
EOF

        echo "✅ Fichier urls.txt généré avec succès !"
        echo "📄 URLs disponibles :"
        echo "  • MP4 Analyser: ${MP4_API_URL}mp4_small_analyser"
        echo "  • Batch: ${MP4_API_URL}batch"
        echo "  • Callback: ${CALLBACK_API_URL}callback"
    else
        echo "⚠️  Impossible de récupérer les URLs des APIs"
    fi
fi

exit $CDK_EXIT_CODE
