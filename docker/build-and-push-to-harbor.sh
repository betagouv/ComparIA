#!/bin/bash

# Script pour builder et pousser les images Docker sur Harbor

set -e

# Configuration Harbor
HARBOR_REGISTRY="55h10w99.gra7.container-registry.ovh.net"
HARBOR_PROJECT="atnum"
BACKEND_IMAGE="$HARBOR_REGISTRY/$HARBOR_PROJECT/languia"
FRONTEND_IMAGE="$HARBOR_REGISTRY/$HARBOR_PROJECT/languia-front"

docker login https://${HARBOR_REGISTRY}/harbor/

# Récupérer le hash long du commit courant
COMMIT_HASH=$(git rev-parse HEAD)
echo "Commit hash: $COMMIT_HASH"

# Tags avec hash du commit
BACKEND_TAG="$BACKEND_IMAGE:$COMMIT_HASH"
FRONTEND_TAG="$FRONTEND_IMAGE:$COMMIT_HASH"

echo "Construction des images Docker..."

# Build l'image backend avec le hash du commit
echo "Build de l'image backend (languia)..."
docker build -t $BACKEND_TAG -f Dockerfile ..

# Build l'image frontend avec le hash du commit
echo "Build de l'image frontend (languia-front)..."
docker build -t $FRONTEND_TAG -f Dockerfile.front ../frontend

echo "Push des images sur Harbor..."

# Push de l'image backend
echo "Push de l'image backend..."
docker push $BACKEND_TAG

# Push de l'image frontend
echo "Push de l'image frontend..."
docker push $FRONTEND_TAG

echo "Images buildées et poussées sur Harbor avec succès !"
echo "Images disponibles :"
echo "- $BACKEND_TAG"
echo "- $FRONTEND_TAG"