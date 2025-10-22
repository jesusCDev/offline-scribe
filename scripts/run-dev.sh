#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "🚀 Starting Silent Scribe (DEV MODE - code changes reflected immediately)..."
echo ""
echo "🔒 Container running with --network none (completely offline)"
echo "🌐 Web UI: http://localhost:7860"
echo "⚠️  DEV MODE: Local app/ directory is mounted"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Ensure data directory exists with correct permissions
mkdir -p data/uploads data/results
chmod -R 777 data/

# Run with network isolation AND mount the app directory for development
sudo docker run --rm -it \
  -p 7860:7860 \
  -v "$(pwd)/data:/data:z" \
  -v "$(pwd)/app:/app:z" \
  --name silent-scribe \
  --network none \
  silent-scribe:latest
