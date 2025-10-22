#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Detect if we need sudo for Docker
DOCKER_CMD="docker"
if ! $DOCKER_CMD ps >/dev/null 2>&1; then
    if sudo $DOCKER_CMD ps >/dev/null 2>&1; then
        DOCKER_CMD="sudo docker"
        echo "ℹ️  Note: Using 'sudo' for Docker commands (you may be prompted for password)"
        echo ""
    fi
fi

echo "🚀 Silent Scribe - Run Script"
echo "============================="
echo ""

# Check if Docker is running, try to start it if not
echo "🔍 Checking Docker..."
if ! $DOCKER_CMD info >/dev/null 2>&1; then
    echo "⚠️  Docker is not running. Attempting to start it..."
    echo ""
    
    # Try systemctl (Linux)
    if command -v systemctl >/dev/null 2>&1; then
        echo "🔑 Starting Docker requires administrator access (you may be asked for your password)"
        sudo systemctl start docker 2>/dev/null && {
            sleep 2
            if $DOCKER_CMD info >/dev/null 2>&1; then
                echo "✓ Docker started successfully"
            else
                echo "❌ Failed to start Docker automatically."
                echo "   Please start Docker manually:"
                echo "     sudo systemctl start docker"
                exit 1
            fi
        } || {
            echo "❌ Could not start Docker (may need password)."
            echo "   Please start Docker manually:"
            echo "     sudo systemctl start docker"
            exit 1
        }
    # Try service command (older Linux)
    elif command -v service >/dev/null 2>&1; then
        echo "   Starting Docker service..."
        sudo service docker start 2>/dev/null && {
            sleep 2
            if $DOCKER_CMD info >/dev/null 2>&1; then
                echo "✓ Docker started successfully"
            else
                echo "❌ Failed to start Docker automatically."
                echo "   Please run: sudo service docker start"
                exit 1
            fi
        } || {
            echo "❌ Could not start Docker (may need password)."
            echo "   Please run: sudo service docker start"
            exit 1
        }
    # Mac with Docker Desktop
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "   Opening Docker Desktop..."
        open -a Docker 2>/dev/null && {
            echo "   Waiting for Docker to start (this may take 10-30 seconds)..."
            for i in {1..30}; do
                if $DOCKER_CMD info >/dev/null 2>&1; then
                    echo "✓ Docker started successfully"
                    break
                fi
                sleep 1
                echo -n "."
            done
            if ! $DOCKER_CMD info >/dev/null 2>&1; then
                echo ""
                echo "❌ Docker Desktop is starting but not ready yet."
                echo "   Please wait a moment and run this script again."
                exit 1
            fi
        } || {
            echo "❌ Could not open Docker Desktop."
            echo "   Please open it manually from Applications."
            exit 1
        }
    else
        echo "❌ Could not determine how to start Docker on this system."
        echo "   Please start Docker manually and run this script again."
        exit 1
    fi
else
    echo "✓ Docker is running"
fi

# Check if image exists
if ! $DOCKER_CMD images silent-scribe:latest | grep -q silent-scribe; then
    echo ""
    echo "❌ Image 'silent-scribe:latest' not found."
    echo "   Please build it first:"
    echo "     ./scripts/build.sh"
    echo "     or: make build"
    exit 1
fi
echo "✓ Image found"

# Stop any existing container (handles Ctrl+C, force-kill, etc.)
echo ""
if $DOCKER_CMD ps -q -f name=silent-scribe | grep -q .; then
    echo "♻️  Found running container, stopping..."
    $DOCKER_CMD stop silent-scribe 2>/dev/null || true
    $DOCKER_CMD rm silent-scribe 2>/dev/null || true
    echo "✓ Cleaned up running container"
elif $DOCKER_CMD ps -aq -f name=silent-scribe | grep -q .; then
    echo "♻️  Found stopped container, removing..."
    $DOCKER_CMD rm silent-scribe 2>/dev/null || true
    echo "✓ Cleaned up stopped container"
else
    echo "✓ No existing container found"
fi

# Ensure data directory exists with correct permissions
echo ""
echo "📁 Preparing data directories..."
mkdir -p data/uploads data/results
chmod -R 777 data/ 2>/dev/null || {
    echo "⚠️  Could not set permissions on data/ (may need sudo)"
}
echo "✓ Data directories ready"

echo ""
echo "=============================="
echo "🚀 Starting Silent Scribe"
echo "=============================="
echo ""
echo "🌐 Web UI:  http://localhost:7860"
echo ""
echo "Features:"
echo "  ✓ Whisper transcription"
echo "  ✓ Llama 2 summarization"
echo "  ✓ Settings persistence"
echo "  ✓ Runs completely offline (no internet access after build)"
echo ""
echo "📝 Tip: Press Ctrl+C to stop (container will auto-cleanup)"
echo ""

# Run container
# Note: We use bridge network mode instead of --network none so you can access
# the web UI from your browser. All models are bundled so no internet is needed.
$DOCKER_CMD run --rm -it \
  -p 7860:7860 \
  -v "$(pwd)/data:/data:z" \
  --name silent-scribe \
  silent-scribe:latest
