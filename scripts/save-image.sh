#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

IMAGE_NAME="silent-scribe:latest"
OUT_DIR="resources"
OUT_FILE="${OUT_DIR}/silent-scribe.tar.gz"

echo "🚀 Silent Scribe - Save Docker Image"
echo "====================================="
echo ""

# Check if Docker is running
echo "🔍 Checking Docker..."
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi
echo "✓ Docker is running"

# Check if image exists
echo ""
echo "🔍 Checking for image '${IMAGE_NAME}'..."
if ! docker images "${IMAGE_NAME}" | grep -q "${IMAGE_NAME}"; then
    echo "❌ Image '${IMAGE_NAME}' not found."
    echo "   Please build it first:"
    echo "     ./scripts/build.sh"
    echo "     or: make build"
    exit 1
fi
echo "✓ Image found"

# Get image info
IMAGE_SIZE=$(docker images "${IMAGE_NAME}" --format "{{.Size}}")
IMAGE_ID=$(docker images "${IMAGE_NAME}" --format "{{.ID}}")
echo "   Size: ${IMAGE_SIZE}"
echo "   ID: ${IMAGE_ID}"

# Check available disk space
echo ""
echo "💾 Checking disk space..."
AVAILABLE_GB=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
echo "   Available: ${AVAILABLE_GB} GB"
if [ "$AVAILABLE_GB" -lt 20 ]; then
    echo "⚠️  Warning: Less than 20 GB free. Export requires ~15-20 GB."
    read -p "   Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create output directory
mkdir -p "${OUT_DIR}"

# Remove old file if exists
if [ -f "${OUT_FILE}" ]; then
    echo ""
    echo "⚠️  File already exists: ${OUT_FILE}"
    read -p "   Overwrite? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Export cancelled."
        exit 0
    fi
    rm -f "${OUT_FILE}"
fi

echo ""
echo "💾 Exporting Docker image..."
echo "   This will take 5-15 minutes depending on your system."
echo ""

# Check if pigz is available for faster compression
if command -v pigz &> /dev/null; then
    echo "✓ Using pigz for faster compression"
    docker image save "${IMAGE_NAME}" | pigz -c > "${OUT_FILE}"
else
    echo "ℹ️  Using gzip (install pigz for faster compression)"
    docker image save "${IMAGE_NAME}" | gzip -c > "${OUT_FILE}"
fi

# Check if export was successful
if [ $? -eq 0 ] && [ -f "${OUT_FILE}" ]; then
    echo ""
    echo "================================"
    echo "✅ Export complete!"
    echo "================================"
    echo ""
    echo "Output file:"
    ls -lh "${OUT_FILE}"
    echo ""
    
    FILE_SIZE_GB=$(du -h "${OUT_FILE}" | cut -f1)
    echo "Compressed size: ${FILE_SIZE_GB}"
    echo ""
    
    echo "Next steps:"
    echo "  1. This file will be bundled with the Electron app"
    echo "  2. Run: npm run dist:linux (or dist:mac, dist:win)"
    echo "  3. The packaged app will include this image"
    echo ""
    echo "⚠️  Note: This file is NOT tracked by git (in .gitignore)"
    echo ""
else
    echo ""
    echo "❌ Export failed!"
    echo "   Check Docker logs and disk space"
    exit 1
fi
