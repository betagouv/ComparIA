#!/bin/bash
set -euo pipefail

# Configuration Harbor
HARBOR_REGISTRY="55h10w99.gra7.container-registry.ovh.net"
HARBOR_PROJECT="atnum"
BACKEND_IMAGE="$HARBOR_REGISTRY/$HARBOR_PROJECT/languia"
FRONTEND_IMAGE="$HARBOR_REGISTRY/$HARBOR_PROJECT/languia-front"

# Login à Harbor
#echo "Connexion à Harbor..."
#echo $HARBOR_PASSWORD | docker login $HARBOR_REGISTRY -u $HARBOR_USER --password-stdin

COMMIT_HASH=$(git rev-parse HEAD)
BRANCH_NAME=$(git rev-parse --abbrev-ref HEAD)

# Tags multiples
BACKEND_TAGS=("$BACKEND_IMAGE:$COMMIT_HASH")
[[ "$BRANCH_NAME" != "main" ]] && BACKEND_TAGS+=("$BACKEND_IMAGE:$BRANCH_NAME")

FRONTEND_TAGS=("$FRONTEND_IMAGE:$COMMIT_HASH")
[[ "$BRANCH_NAME" != "main" ]] && FRONTEND_TAGS+=("$FRONTEND_IMAGE:$BRANCH_NAME")

# Setup buildx
docker buildx create --name comparia-builder --use --bootstrap 2>/dev/null || docker buildx use comparia-builder
docker buildx inspect --bootstrap

# Build arguments
BUILD_ARGS=(
  "--build-arg" "GIT_COMMIT=$COMMIT_HASH"
  "--build-arg" "PUBLIC_API_URL=${PUBLIC_API_URL:-}"
  "--build-arg" "MATOMO_ID=${MATOMO_ID:-}"
  "--build-arg" "MATOMO_URL=${MATOMO_URL:-}"
)

echo "Construction parallèle des images avec buildx..."

# Construction parallèle
{
  # Backend
  echo "Build backend..."
  docker buildx build \
    "${BUILD_ARGS[@]}" \
    $(printf -- "-t %s " "${BACKEND_TAGS[@]}") \
    -f Dockerfile \
    --push \
    .. &
  
  BACKEND_PID=$!
  
  # Frontend
  echo "Build frontend..."  
  docker buildx build \
    "${BUILD_ARGS[@]}" \
    $(printf -- "-t %s " "${FRONTEND_TAGS[@]}") \
    -f Dockerfile.front \
    --push \
    ../frontend &
  
  FRONTEND_PID=$!
  
  # Attendre les deux builds
  wait $BACKEND_PID
  echo "✅ Backend build terminé"
  wait $FRONTEND_PID  
  echo "✅ Frontend build terminé"
}

echo "Images buildées et poussées avec succès !"
echo "Backend: ${BACKEND_TAGS[*]}"
echo "Frontend: ${FRONTEND_TAGS[*]}"