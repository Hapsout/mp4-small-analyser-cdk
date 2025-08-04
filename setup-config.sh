#!/bin/bash

# Script de configuration pour MP4 Small Analyser CDK
# Ce script génère le fichier .env avec les paramètres personnalisés

set -e

CONFIG_FILE=".env"
EXAMPLE_FILE=".env.example"

echo "🚀 Configuration de MP4 Small Analyser CDK"
echo "=========================================="
echo ""

# Vérifier si le fichier de config existe déjà
if [ -f "$CONFIG_FILE" ]; then
    echo "⚠️  Un fichier de configuration existe déjà."
    read -p "Voulez-vous le remplacer ? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Configuration annulée."
        exit 0
    fi
    echo ""
fi

echo "📝 Veuillez renseigner les paramètres de configuration:"
echo ""

# Fonction pour demander une valeur avec une valeur par défaut
ask_with_default() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " value
        if [ -z "$value" ]; then
            value="$default"
        fi
    else
        read -p "$prompt: " value
        while [ -z "$value" ]; do
            echo "⚠️  Cette valeur est obligatoire."
            read -p "$prompt: " value
        done
    fi
    
    # Exporter la variable pour l'utiliser plus tard
    export "$var_name"="$value"
}

# Fonction pour valider un ID de compte AWS
validate_aws_account() {
    if [[ ! $1 =~ ^[0-9]{12}$ ]]; then
        echo "⚠️  L'ID de compte AWS doit contenir exactement 12 chiffres."
        return 1
    fi
    return 0
}

# Fonction pour valider une région AWS
validate_aws_region() {
    local region="$1"
    # Liste des régions AWS principales
    local valid_regions=(
        "us-east-1" "us-east-2" "us-west-1" "us-west-2"
        "eu-west-1" "eu-west-2" "eu-west-3" "eu-central-1" "eu-north-1"
        "ap-southeast-1" "ap-southeast-2" "ap-northeast-1" "ap-northeast-2"
        "ca-central-1" "sa-east-1"
    )
    
    for valid_region in "${valid_regions[@]}"; do
        if [ "$region" = "$valid_region" ]; then
            return 0
        fi
    done
    
    echo "⚠️  Région non reconnue. Voulez-vous continuer quand même ? (y/N): "
    read -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        return 0
    else
        return 1
    fi
}

echo "🔧 Configuration AWS"
echo "-------------------"

# ID de compte AWS
while true; do
    ask_with_default "ID de compte AWS" "$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo '')" "AWS_ACCOUNT_ID"
    if validate_aws_account "$AWS_ACCOUNT_ID"; then
        break
    fi
done

# Région AWS
while true; do
    ask_with_default "Région AWS" "eu-west-1" "AWS_REGION"
    if validate_aws_region "$AWS_REGION"; then
        break
    fi
done

# Profil AWS
ask_with_default "Profil AWS" "default" "AWS_PROFILE"

echo ""
echo "🏗️  Configuration du projet"
echo "-------------------------"

# Nom du projet
ask_with_default "Nom du projet" "mp4-small-analyser" "PROJECT_NAME"

# Client
ask_with_default "Nom du client" "default-client" "CLIENT"

# Projet (pour les tags)
ask_with_default "Nom du projet (pour les tags)" "mp4-small-analyser" "PROJECT"

# Environnement
echo "Environnement (dev/staging/prod):"
select env in "dev" "staging" "prod" "autre"; do
    case $env in
        dev|staging|prod)
            ENVIRONMENT="$env"
            break
            ;;
        autre)
            ask_with_default "Nom de l'environnement" "dev" "ENVIRONMENT"
            break
            ;;
        *)
            echo "Veuillez choisir une option valide."
            ;;
    esac
done

echo ""
echo "⚙️  Configuration avancée (optionnel)"
echo "-----------------------------------"

# Configuration des stacks
ask_with_default "Nom de la stack principale" "${PROJECT_NAME^}CdkStack" "MAIN_STACK_NAME"
ask_with_default "Nom de la stack callback" "${PROJECT_NAME^}CallbackStack" "CALLBACK_STACK_NAME"

# Configuration DynamoDB
ask_with_default "Nom de la table DynamoDB" "${PROJECT_NAME}-callback-results" "DYNAMODB_TABLE_NAME"

# Configuration API Gateway
ask_with_default "Stage API Gateway" "prod" "API_GATEWAY_STAGE"

# Configuration Lambda
ask_with_default "Timeout Lambda (secondes)" "30" "LAMBDA_TIMEOUT"
ask_with_default "Mémoire Lambda (MB)" "256" "LAMBDA_MEMORY_SIZE"

# Configuration de debug
echo "Mode debug:"
select debug in "false" "true"; do
    case $debug in
        false|true)
            DEBUG_MODE="$debug"
            break
            ;;
        *)
            echo "Veuillez choisir une option valide."
            ;;
    esac
done

echo "Niveau de log:"
select log_level in "INFO" "DEBUG" "WARNING" "ERROR"; do
    case $log_level in
        INFO|DEBUG|WARNING|ERROR)
            LOG_LEVEL="$log_level"
            break
            ;;
        *)
            echo "Veuillez choisir une option valide."
            ;;
    esac
done

echo ""
echo "💾 Génération du fichier de configuration..."

# Créer le fichier .env
cat > "$CONFIG_FILE" << EOF
# Configuration AWS CDK pour MP4 Small Analyser
# Généré le $(date '+%Y-%m-%d %H:%M:%S')

# Configuration AWS
AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID
AWS_REGION=$AWS_REGION
AWS_PROFILE=$AWS_PROFILE

# Configuration du projet
PROJECT_NAME=$PROJECT_NAME
ENVIRONMENT=$ENVIRONMENT

# Tags de projet
CLIENT=$CLIENT
PROJECT=$PROJECT

# Configuration des stacks
MAIN_STACK_NAME=$MAIN_STACK_NAME
CALLBACK_STACK_NAME=$CALLBACK_STACK_NAME

# Configuration DynamoDB
DYNAMODB_TABLE_NAME=$DYNAMODB_TABLE_NAME

# Configuration API Gateway
API_GATEWAY_STAGE=$API_GATEWAY_STAGE

# Configuration Lambda
LAMBDA_TIMEOUT=$LAMBDA_TIMEOUT
LAMBDA_MEMORY_SIZE=$LAMBDA_MEMORY_SIZE

# Configuration de débogage
DEBUG_MODE=$DEBUG_MODE
LOG_LEVEL=$LOG_LEVEL
EOF

echo "✅ Fichier de configuration créé: $CONFIG_FILE"
echo ""
echo "📋 Résumé de la configuration:"
echo "  • Compte AWS: $AWS_ACCOUNT_ID"
echo "  • Région: $AWS_REGION"
echo "  • Profil: $AWS_PROFILE"
echo "  • Projet: $PROJECT_NAME"
echo "  • Environnement: $ENVIRONMENT"
echo ""
echo "🔒 Le fichier .env a été ajouté au .gitignore pour la sécurité."
echo ""
echo "💡 Prochaines étapes:"
echo "  1. Vérifiez que votre profil AWS est configuré: aws configure --profile $AWS_PROFILE"
echo "  2. Bootstrappez CDK si nécessaire: cdk bootstrap --profile $AWS_PROFILE"
echo "  3. Déployez vos stacks: cdk deploy --all --profile $AWS_PROFILE"
echo ""
echo "🎉 Configuration terminée !"
