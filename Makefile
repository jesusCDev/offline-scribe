.PHONY: build run stop clean help

help:
	@echo "Silent Scribe - Air-Gapped Video Transcription"
	@echo ""
	@echo "Available targets:"
	@echo "  make build    - Build the Docker image with all models"
	@echo "  make run      - Run the container (air-gapped)"
	@echo "  make stop     - Stop the running container"
	@echo "  make clean    - Remove the Docker image"
	@echo "  make help     - Show this help message"

build:
	@./scripts/build.sh

run:
	@./scripts/run.sh

stop:
	@./scripts/stop.sh

clean:
	@echo "🗑️  Removing Silent Scribe image..."
	@docker rmi silent-scribe:latest || true
	@echo "✅ Cleaned"
