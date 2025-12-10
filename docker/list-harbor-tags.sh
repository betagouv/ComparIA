#!/bin/bash

# Script pour lister les tags existants sur Harbor pour les images languia et languia-front

set -e

# Configuration Harbor
HARBOR_REGISTRY="55h10w99.gra7.container-registry.ovh.net"
HARBOR_PROJECT="atnum"

# Images à lister
BACKEND_IMAGE="$HARBOR_PROJECT/languia"
FRONTEND_IMAGE="$HARBOR_PROJECT/languia-front"

# Vérifier les credentials
if [ -n "$HARBOR_USERNAME" ] && [ -n "$HARBOR_PASSWORD" ]; then
    AUTH="-u $HARBOR_USERNAME:$HARBOR_PASSWORD"
    echo "Utilisation des credentials Harbor"
else
    AUTH=""
    echo "Aucun credentials détectés, tentative sans authentification"
fi

echo "=== Tags pour $BACKEND_IMAGE ==="
# Lister les tags du backend
BACKEND_TAGS=$(curl -s $AUTH "https://$HARBOR_REGISTRY/v2/$BACKEND_IMAGE/tags/list" 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$BACKEND_TAGS" ]; then
    echo $BACKEND_TAGS | jq -r '.tags[]' 2>/dev/null || echo $BACKEND_TAGS
else
    echo "Erreur: Impossible de récupérer les tags pour $BACKEND_IMAGE"
fi

echo ""
echo "=== Tags pour $FRONTEND_IMAGE ==="
# Lister les tags du frontend
FRONTEND_TAGS=$(curl -s $AUTH "https://$HARBOR_REGISTRY/v2/$FRONTEND_IMAGE/tags/list" 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$FRONTEND_TAGS" ]; then
    echo $FRONTEND_TAGS | jq -r '.tags[]' 2>/dev/null || echo $FRONTEND_TAGS
else
    echo "Erreur: Impossible de récupérer les tags pour $FRONTEND_IMAGE"
fi

echo ""
echo "=== Configuration des credentials (optionnel) ==="
echo "Si authentification requise, exportez :"
echo "export HARBOR_USERNAME='votre-username'"
echo "export HARBOR_PASSWORD='votre-password'"
echo "Puis réexécutez: ./docker/list-harbor-tags.sh"