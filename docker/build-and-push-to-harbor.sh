#!/bin/bash
set -euo pipefail

# Se positionner à la racine du projet
cd "$(dirname "$0")/.."

# Configuration Harbor
export HARBOR_REGISTRY="55h10w99.gra7.container-registry.ovh.net"
export HARBOR_PROJECT="atnum"

# Git info
export GIT_COMMIT=$(git rev-parse HEAD)
export BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)

# Build args (optionnels)
export PUBLIC_API_URL="${PUBLIC_API_URL:-}"
export MATOMO_ID="${MATOMO_ID:-}"
export MATOMO_URL="${MATOMO_URL:-}"

# Setup buildx
docker buildx create --name comparia-builder --use --bootstrap 2>/dev/null || docker buildx use comparia-builder
docker buildx inspect --bootstrap

echo "Build des images avec docker bake..."
docker buildx bake -f docker/docker-bake.yml --push

echo "Images buildées et poussées avec succès !"
echo "Backend: $HARBOR_REGISTRY/$HARBOR_PROJECT/languia:$GIT_COMMIT"
echo "Frontend: $HARBOR_REGISTRY/$HARBOR_PROJECT/languia-front:$GIT_COMMIT"
[[ "$BRANCH_NAME" != "main" ]] && echo "Tags branch: $BRANCH_NAME"
