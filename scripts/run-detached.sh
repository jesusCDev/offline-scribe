#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "🚀 Starting Silent Scribe in background (detached mode)..."
echo ""
echo "🌐 Web UI will be available at: http://localhost:7860"
echo "⚠️  Running WITHOUT --network none for development/testing"
echo ""

# Ensure data directory exists with correct permissions
mkdir -p data/uploads data/results
chmod -R 777 data/

# Stop existing container if running
sudo docker stop silent-scribe 2>/dev/null || true
sudo docker rm silent-scribe 2>/dev/null || true

# Run in detached mode
sudo docker run -d \
  -p 7860:7860 \
  -v "$(pwd)/data:/data:z" \
  --name silent-scribe \
  --restart unless-stopped \
  silent-scribe:latest

echo ""
echo "✅ Container started!"
echo "🌐 Visit: http://localhost:7860"
echo ""
echo "To view logs:    sudo docker logs -f silent-scribe"
echo "To stop:         sudo docker stop silent-scribe"
echo ""
