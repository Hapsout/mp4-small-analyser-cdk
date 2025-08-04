#!/bin/bash

echo "=== Test de l'API avec le nouveau formatage ==="
echo "Fichier utilisé: mp4_simple_avec_ids.json"
echo "URL: https://4omwm7b5ul.execute-api.eu-west-1.amazonaws.com/prod/mp4_small_analyser"
echo ""

curl -X POST "https://4omwm7b5ul.execute-api.eu-west-1.amazonaws.com/prod/mp4_small_analyser" \
  -H "Content-Type: application/json" \
  -d @"/home/boubou/code/hapsout/mp4-small-analyser-cdk/exemples/mp4_simple_avec_ids.json" \
  -w "\n\nStatus: %{http_code}\nTime: %{time_total}s\n"

echo ""
echo "=== Test de l'API Batch avec le nouveau formatage ==="
echo "Fichier utilisé: batch_avec_ids_mixtes.json"
echo "URL: https://4omwm7b5ul.execute-api.eu-west-1.amazonaws.com/prod/batch"
echo ""

curl -X POST "https://4omwm7b5ul.execute-api.eu-west-1.amazonaws.com/prod/batch" \
  -H "Content-Type: application/json" \
  -d @"/home/boubou/code/hapsout/mp4-small-analyser-cdk/exemples/batch_avec_ids_mixtes.json" \
  -w "\n\nStatus: %{http_code}\nTime: %{time_total}s\n"
