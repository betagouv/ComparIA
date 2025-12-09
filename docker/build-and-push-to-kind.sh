#!/bin/bash

# Script pour builder et pousser les images Docker dans un cluster kind local

set -e

# Récupérer le hash long du commit courant
COMMIT_HASH=$(git rev-parse HEAD)
echo "Commit hash: $COMMIT_HASH"

echo "Construction des images Docker..."

# Build l'image backend avec le hash du commit
echo "Build de l'image backend (languia)..."
docker build -t languia:$COMMIT_HASH -f Dockerfile ..

# Build l'image frontend avec le hash du commit
echo "Build de l'image frontend (languia-front)..."
docker build -t languia-front:$COMMIT_HASH -f Dockerfile.front ../frontend

echo "Chargement des images dans le cluster kind..."

# Charger les images dans kind
kind load docker-image --name kind-comparia languia:$COMMIT_HASH
kind load docker-image --name kind-comparia languia-front:$COMMIT_HASH

echo "Images buildées et chargées dans kind avec succès !"
echo "Images disponibles :"
echo "- languia:$COMMIT_HASH"
echo "- languia-front:$COMMIT_HASH"
