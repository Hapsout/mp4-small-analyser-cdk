# Mode DEBUG - MP4 Analyser

## 🐛 Activation du mode DEBUG

Pour activer les logs de debug détaillés dans CloudWatch, définissez la variable d'environnement :

```bash
DEBUG=true
```

## 📋 Informations loggées en mode DEBUG

Quand `DEBUG=true`, les informations suivantes sont automatiquement loggées dans CloudWatch :

### 1. Résultat brut de l'analyse

```
[DEBUG] Résultat de l'analyse pour task_id xxx: {
  "silencePercentage": 0,
  "loudnessMeasured": -24.1,
  "loudnessTruePeak": -7.8,
  "audioDuration": 20.01,
  "videoDuration": 20.01,
  "processing_time": 1.37
}
```

### 2. Données complètes du callback

```
[DEBUG] Données de callback complètes pour task_id xxx: {
  "status": "completed",
  "results": { ... },
  "task_id": "xxx",
  "processing_time": 1.37,
  "metadata": { ... }
}
```

### 3. Détails de l'envoi du callback

```
[DEBUG] Envoi callback POST vers: https://webhook.site/xxx?user_id=123
[DEBUG] Données envoyées: { ... }
```

## 🔧 Configuration dans CDK

Pour activer le DEBUG via CDK, ajoutez dans votre stack :

```python
mp4_analyser_lambda = aws_lambda.Function(
    self,
    "Mp4AnalyserLambda",
    # ... autres paramètres
    environment={
        "DEBUG": "true"  # ← Ajouter cette ligne
    }
)
```

## 📊 Consultation des logs

### Via AWS Console

1. Allez dans CloudWatch > Log groups
2. Cherchez `/aws/lambda/your-function-name`
3. Filtrez par `[DEBUG]` pour voir uniquement les logs de debug

### Via AWS CLI

```bash
# Voir les logs en temps réel avec filtre DEBUG
aws logs filter-log-events \
    --log-group-name "/aws/lambda/your-function-name" \
    --filter-pattern "[DEBUG]" \
    --start-time $(date -d "1 hour ago" +%s)000

# Voir les logs d'une requête spécifique
aws logs filter-log-events \
    --log-group-name "/aws/lambda/your-function-name" \
    --filter-pattern "task_id_here"
```

## ⚠️ Important

- Le mode DEBUG génère beaucoup plus de logs → coût CloudWatch plus élevé
- Désactivez en production sauf pour le dépannage
- Les logs peuvent contenir des données sensibles (URLs, métadonnées)

## 💡 Utilisation recommandée

```python
# En développement
DEBUG=true

# En production
DEBUG=false  # ou ne pas définir la variable
```
