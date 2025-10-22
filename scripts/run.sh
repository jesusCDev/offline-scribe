#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "🚀 Starting Silent Scribe (air-gapped mode)..."
echo ""
echo "🔒 Container running with --network none (completely offline)"
echo "🌐 Web UI: http://localhost:7860"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Ensure data directory exists
mkdir -p data/uploads data/results

# Run with network isolation
docker run --rm -it \
  -p 7860:7860 \
  -v "$(pwd)/data:/data" \
  --name silent-scribe \
  --network none \
  silent-scribe:latest
