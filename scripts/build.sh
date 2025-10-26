#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "🚀 Silent Scribe - Build Script"
echo "================================"
echo ""

# Check if Docker is running
echo "🔍 Checking Docker..."
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi
echo "✓ Docker is running"

# Check if image already exists
if docker images silent-scribe:latest | grep -q silent-scribe; then
    echo ""
    echo "⚠️  Image 'silent-scribe:latest' already exists."
    echo "   This will rebuild it with the latest code."
    read -p "   Continue? (Y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        echo "Build cancelled."
        exit 0
    fi
fi

# Check available disk space
echo ""
echo "💾 Checking disk space..."
AVAILABLE_GB=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
echo "   Available: ${AVAILABLE_GB} GB"
if [ "$AVAILABLE_GB" -lt 30 ]; then
    echo "⚠️  Warning: Less than 30 GB free. Build requires ~27 GB total."
    read -p "   Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create data directories with correct permissions
echo ""
echo "📁 Setting up data directories..."
mkdir -p data/uploads data/results
chmod -R 777 data/ 2>/dev/null || true
echo "✓ Data directories ready"

# Load HF_TOKEN from .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "✓ Loaded HF_TOKEN from .env (for optional speaker diarization)"
else
    echo "ℹ️  No .env file (speaker diarization will be disabled)"
fi

# Get version from package.json if it exists, otherwise default
if [ -f package.json ]; then
    IMAGE_VERSION=$(grep '"version":' package.json | head -1 | sed 's/.*"version": "\(.*\)".*/\1/')
else
    IMAGE_VERSION="0.1.0"
fi

BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo ""
echo "🔨 Starting Docker build..."
echo "   Version: ${IMAGE_VERSION}"
echo "   This will take 30-60 minutes and download:"
echo "   - Whisper models (~15 GB)"
echo "   - Llama 2 model (~4 GB)"
echo "   - Total image size: ~27 GB"
echo ""

# Build for current architecture
if docker build \
  --build-arg HF_TOKEN="${HF_TOKEN:-}" \
  --build-arg IMAGE_VERSION="${IMAGE_VERSION}" \
  --build-arg BUILD_DATE="${BUILD_DATE}" \
  --build-arg CACHEBUST=$(date +%s) \
  -t silent-scribe:latest \
  -f docker/Dockerfile \
  . ; then
    
    echo ""
    echo "="==============================="
    echo "✅ Build complete!"
    echo "="==============================="
    echo ""
    echo "Image info:"
    docker images silent-scribe:latest --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    echo ""
    echo "Features included:"
    echo "  ✓ Whisper transcription (5 models, 2 engines)"
    echo "  ✓ Llama 2 7B summarization"
    echo "  ✓ Settings persistence"
    echo "  ✓ Air-gapped operation"
    echo ""
    echo "Next steps:"
    echo "  Run:  ./scripts/run.sh"
    echo "  Or:   make run"
    echo ""
else
    echo ""
    echo "❌ Build failed!"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check Docker logs above for errors"
    echo "  2. Ensure you have ~30 GB free disk space"
    echo "  3. Try: docker system prune -a (to free space)"
    echo "  4. Retry the build"
    exit 1
fi
