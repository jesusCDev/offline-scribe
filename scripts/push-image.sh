#!/usr/bin/env bash
# Push Docker image to GitHub Container Registry for use in CI/CD
set -euo pipefail

IMAGE_NAME="silent-scribe:latest"
REGISTRY="ghcr.io"
REPO_OWNER="jesuscdev"
REPO_NAME="offline-scribe"
REGISTRY_IMAGE="${REGISTRY}/${REPO_OWNER}/${REPO_NAME}:latest"

echo "🚀 Pushing Docker Image to GitHub Container Registry"
echo "=================================================="
echo ""

# Check if image exists locally
echo "🔍 Checking for local image: ${IMAGE_NAME}"
if ! docker image inspect "${IMAGE_NAME}" &>/dev/null; then
    echo "❌ Error: Image '${IMAGE_NAME}' not found locally."
    echo "   Please build the image first:"
    echo "   ./scripts/build.sh"
    exit 1
fi
echo "✓ Image found"
echo ""

# Get version from image label
VERSION=$(docker image inspect "${IMAGE_NAME}" --format '{{index .Config.Labels "org.opencontainers.image.version"}}' 2>/dev/null || echo "unknown")
echo "📦 Image version: ${VERSION}"
echo ""

# Check if logged in to GHCR
echo "🔐 Checking GitHub Container Registry authentication..."
if ! docker info 2>/dev/null | grep -q "ghcr.io"; then
    echo "⚠️  Not logged in to GitHub Container Registry."
    echo ""
    echo "Please login with:"
    echo "  echo \$GITHUB_TOKEN | docker login ghcr.io -u ${REPO_OWNER} --password-stdin"
    echo ""
    echo "Generate a token at: https://github.com/settings/tokens"
    echo "Required scopes: write:packages, read:packages"
    echo ""
    exit 1
fi
echo "✓ Authenticated"
echo ""

# Tag for registry
echo "🏷️  Tagging image for registry..."
docker tag "${IMAGE_NAME}" "${REGISTRY_IMAGE}"
if [ "${VERSION}" != "unknown" ] && [ "${VERSION}" != "latest" ]; then
    VERSIONED_IMAGE="${REGISTRY}/${REPO_OWNER}/${REPO_NAME}:${VERSION}"
    docker tag "${IMAGE_NAME}" "${VERSIONED_IMAGE}"
    echo "✓ Tagged: ${VERSIONED_IMAGE}"
fi
echo "✓ Tagged: ${REGISTRY_IMAGE}"
echo ""

# Push to registry
echo "⬆️  Pushing to GitHub Container Registry..."
echo "   This will take several minutes (~15-20 GB)..."
echo ""
docker push "${REGISTRY_IMAGE}"

if [ "${VERSION}" != "unknown" ] && [ "${VERSION}" != "latest" ]; then
    docker push "${VERSIONED_IMAGE}"
fi

echo ""
echo "✅ Push complete!"
echo ""
echo "Image available at:"
echo "  ${REGISTRY_IMAGE}"
if [ "${VERSION}" != "unknown" ] && [ "${VERSION}" != "latest" ]; then
    echo "  ${VERSIONED_IMAGE}"
fi
echo ""
echo "To use in GitHub Actions, make sure the package is public:"
echo "  https://github.com/${REPO_OWNER}/${REPO_NAME}/pkgs/container/${REPO_NAME}/settings"
