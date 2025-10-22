#!/usr/bin/env bash
set -euo pipefail

echo "🛑 Stopping Silent Scribe..."
docker stop silent-scribe || echo "Container not running"
echo "✅ Stopped"
