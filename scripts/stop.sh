#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Detect if we need sudo for Docker
DOCKER_CMD="docker"
if ! $DOCKER_CMD ps >/dev/null 2>&1; then
    if sudo $DOCKER_CMD ps >/dev/null 2>&1; then
        DOCKER_CMD="sudo docker"
    fi
fi

# Check if Docker is running
if ! $DOCKER_CMD info >/dev/null 2>&1; then
    echo "❌ Docker is not running."
    exit 1
fi

# Check for running container first
if $DOCKER_CMD ps -q -f name=silent-scribe | grep -q .; then
    echo "🛑 Stopping running Silent Scribe container..."
    $DOCKER_CMD stop silent-scribe >/dev/null 2>&1 || true
    $DOCKER_CMD rm silent-scribe >/dev/null 2>&1 || true
    echo "✅ Stopped and removed container"
# Check for stopped container
elif $DOCKER_CMD ps -aq -f name=silent-scribe | grep -q .; then
    echo "🧹 Removing stopped Silent Scribe container..."
    $DOCKER_CMD rm silent-scribe >/dev/null 2>&1 || true
    echo "✅ Removed container"
else
    echo "ℹ️  No silent-scribe container found (already stopped)"
fi
