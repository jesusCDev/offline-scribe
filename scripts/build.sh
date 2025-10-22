#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Building Silent Scribe Docker image..."
echo "⚠️  This will take a while (downloading and bundling all models)"
echo ""

cd "$(dirname "$0")/.."

# Build for current architecture
docker build \
  -t silent-scribe:latest \
  -f docker/Dockerfile \
  .

echo ""
echo "✅ Build complete!"
echo ""
echo "Image size:"
docker images silent-scribe:latest
echo ""
echo "To run: ./scripts/run.sh"
