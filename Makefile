.PHONY: build run run-dev run-detached stop clean help

help:
	@echo "Silent Scribe - Air-Gapped Video Transcription"
	@echo ""
	@echo "Available targets:"
	@echo "  make build        - Build the Docker image with all models"
	@echo "  make run          - Run the container (air-gapped, interactive)"
	@echo "  make run-dev      - Run with local code mounted (for development)"
	@echo "  make run-detached - Run in background (for testing, no network isolation)"
	@echo "  make stop         - Stop the running container"
	@echo "  make clean        - Remove the Docker image"
	@echo "  make help         - Show this help message"

build:
	@./scripts/build.sh

run:
	@./scripts/run.sh

run-dev:
	@./scripts/run-dev.sh

run-detached:
	@./scripts/run-detached.sh

stop:
	@./scripts/stop.sh

clean:
	@echo "🗑️  Removing Silent Scribe image..."
	@docker rmi silent-scribe:latest || true
	@echo "✅ Cleaned"
