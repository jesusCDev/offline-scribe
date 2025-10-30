# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Silent Scribe** is a completely air-gapped, offline video transcription system with AI-powered summarization. It uses Whisper for transcription and Llama 2 7B for summarization, all running locally without internet access.

The project has two distinct runtime architectures:
1. **Docker-based**: Core transcription service running in an isolated container
2. **Electron Desktop App**: Cross-platform GUI wrapper that manages Docker containers

## Common Commands

### Docker Development
```bash
# Build the Docker image (downloads ~27GB of models, takes 30-60 min)
./build
# or
make build

# Run the container (air-gapped mode with --network none)
./start
# or
make run

# Stop the container
make stop
# or press Ctrl+C

# Run with local code mounted (for backend development)
make run-dev

# Save Docker image for distribution
./save-image
# Creates silent-scribe-image.tar.gz (~27GB)

# Load pre-built image
./load
```

### Electron App Development
```bash
# Install dependencies
npm install

# Run in development mode
npm run dev

# Build distributable packages
npm run dist              # All platforms
npm run dist:linux        # Linux (AppImage, deb)
npm run dist:mac          # macOS (dmg)
npm run dist:win          # Windows (nsis)
```

### Testing
```bash
# Test edge cases
./scripts/test-edge-cases.sh
```

## Architecture

### Multi-Layer Design

**Layer 1: Docker Container (Backend)**
- **FastAPI Backend**: `app/backend/main.py` - REST API with SSE for real-time updates
- **Transcription Engines**: Two engines with different performance characteristics
  - `faster_whisper_engine.py`: CTranslate2-based, better progress tracking
  - `whisper_cpp_engine.py`: GGML-based, faster on Apple Silicon
- **Summarization**: `llama_engine.py` - Uses llama.cpp with map-reduce for long transcripts
- **Job Management**: `job_manager.py` - Single-job enforcement with busy locking to prevent concurrent transcription/summarization
- **Model Management**: `model_manager.py` - Runtime model download/deletion via UI
- **Web UI**: `app/templates/index.html` - Tabbed interface with drag-and-drop uploads

**Layer 2: Electron Wrapper (Desktop App)**
- **Main Process**: `electron/main.js` - Manages lifecycle, IPC handlers, settings persistence
- **Docker Manager**: `electron/docker-manager.js` - Handles Docker operations (image load/build, container lifecycle)
- **Logger**: `electron/logger.js` - File rotation logging system
- **Splash Screen**: `electron/splash.html` - Startup UI with offline mode toggle

### Key Design Patterns

**Air-Gapped Security**:
- Container runs with `--network none` (configurable via Electron settings)
- All models bundled at build time in Docker image
- Environment variables: `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`
- No CDN dependencies in frontend

**Concurrent Safety**:
- `JobManager._is_busy` flag prevents simultaneous transcription + summarization
- Async locks protect job state transitions (app/backend/job_manager.py:43-44)
- Only one transcription/summarization task runs at a time

**State Management**:
- Jobs persisted as JSON in `/data/results/{job_id}/job.json`
- Settings persisted in Electron userData directory
- Frontend polls `/api/jobs/{job_id}/status` for updates

**Model Management**:
- Only `tiny` model ships by default to keep image small
- Users download additional models via UI at runtime
- Models stored in `/opt/models` with separate dirs for faster-whisper and whisper.cpp

### Critical File Locations

**Backend Core**:
- `app/backend/main.py` - All API endpoints, background task orchestration
- `app/backend/config.py` - Paths, defaults, feature flags (SUMMARIZATION_AVAILABLE)
- `app/backend/job_manager.py` - Job lifecycle, busy locking (lines 43-196)
- `app/backend/model_manager.py` - Model download/delete operations

**Transcription Engines**:
- `app/backend/engines/faster_whisper_engine.py` - CTranslate2 engine
- `app/backend/engines/whisper_cpp_engine.py` - GGML engine with subprocess
- `app/backend/engines/llama_engine.py` - Summarization with chunking

**Electron Desktop**:
- `electron/main.js` - IPC handlers, window management (lines 195-518)
- `electron/docker-manager.js` - Docker API interactions
- `electron/splash.html` - Bootstrap UI with offline toggle

**Build System**:
- `docker/Dockerfile` - Multi-stage build with model fetching
- `scripts/fetch_models.py` - Model download script (build-time + runtime)
- `scripts/build.sh` - Docker build wrapper
- `scripts/run.sh` - Container startup with platform detection

## Development Workflows

### Adding a New API Endpoint
1. Add route handler in `app/backend/main.py`
2. Update frontend in `app/templates/index.html` to call endpoint
3. Test with `make run-dev` (live code mounting)

### Modifying Transcription Engines
1. Edit engine file in `app/backend/engines/`
2. Engines must implement: `transcribe(audio_path, job_dir, model, settings, progress_callback)`
3. Return dict with paths: `{"txt": Path, "srt": Path, "vtt": Path}`
4. Use progress_callback(0-100) for UI updates

### Adding Model Support
1. Update `AVAILABLE_MODELS` in `app/backend/config.py:47`
2. Add model info to `ModelManager.AVAILABLE_MODELS` in `model_manager.py`
3. Update `scripts/fetch_models.py` if new model sources needed

### Electron App Changes
1. Backend changes: Rebuild Docker image with `./build`
2. Frontend changes: Edit `electron/splash.html` (no rebuild needed for testing)
3. IPC handlers: Add in `electron/main.js` (lines 188-518)
4. Test with `npm run dev` before packaging

### Packaging for Distribution
1. Build Docker image: `./build`
2. Save image: `./save-image` → creates `silent-scribe-image.tar.gz`
3. Place in `resources/` directory for Electron bundling
4. Build Electron app: `npm run dist:linux` (or platform of choice)
5. Users run `./load` to import image, then `./start` to run

## Important Constraints

**Security**:
- NEVER remove `--network none` from default run configuration
- All external dependencies MUST be bundled at build time
- No runtime API calls to external services

**Concurrency**:
- Only ONE transcription OR summarization task can run at a time
- Check `JobManager._is_busy` before starting tasks (job_manager.py:44)
- Always release busy lock in completed/failed/error states

**Memory**:
- Large models (medium, large-v3) require 8-16GB RAM
- Summarization adds ~4GB peak memory usage
- Electron app runs container with host memory limits

**Platform Support**:
- Docker required on all platforms
- Electron app handles platform-specific Docker socket paths
- Scripts use bash (Git Bash on Windows)

## Settings and Configuration

**Docker Environment**:
- `APP_PORT=7860` - FastAPI port inside container
- `HF_HOME=/opt/hf` - Hugging Face cache
- Models: `/opt/models/{faster-whisper,whisper.cpp,llama}/`
- Data: `/data` mounted from host

**Electron Settings** (`~/.config/silent-scribe/settings.json`):
- `offlineMode`: true/false - Controls `--network none` flag
- Persisted across app restarts

**Build Args**:
- `IMAGE_VERSION` - Semantic version for image metadata
- `BUILD_DATE` - ISO timestamp
- `HF_TOKEN` - Optional Hugging Face token for pyannote models
- `CACHEBUST` - Force model refetch during build

## Logs and Debugging

**Electron Logs**:
- Location: `~/.config/silent-scribe/logs/`
- Rotation: Daily, keeps last 7 days
- Access via UI: Splash screen → "View Logs" button
- Read programmatically: `logger.readRecentLogs(lines)`

**Docker Logs**:
```bash
docker logs silent-scribe -f
```

**Backend Errors**:
- Job errors stored in `job.error` field (job_manager.py:102)
- Summary errors in `job.summary.error` (job_manager.py:224)
- HTTP 409 when system busy, 404 for missing jobs

## Common Pitfalls

1. **Forgetting busy lock**: Always use `JobManager.start_summarization()` before summarization to acquire lock
2. **Direct model paths**: Use `config.py` constants (LLAMA_MODEL_PATH, etc.) not hardcoded paths
3. **Async deadlock**: Don't call async lock methods inside lock context (see job_manager.py:182-196)
4. **Progress ranges**: Engines must report 10-95% progress (0-10% reserved for audio extraction, 95-100% for finalization)
5. **Audio extraction**: Always check ffmpeg stderr for "no audio track" errors (main.py:438-443)
6. **Electron IPC**: Use `ipcMain.handle()` for async operations, not `ipcMain.on()`
7. **Docker networking**: Test offline mode with both `--network none` AND online mode for model downloads

## Recent Development History (2025-10-27)

### Completed Features ✅

**1. Lite Docker Image (2.73 GB)**
- Modified Dockerfile to ship only `tiny` model by default
- Reduced image from 19.1 GB → 2.73 GB
- Users download additional models via UI at runtime
- Published to private GHCR: `ghcr.io/jesuscdev/offline-scribe:latest`

**2. Offline Mode Toggle**
- UI toggle in splash screen for air-gapped mode (default: ON)
- Settings persisted in `~/.config/Silent Scribe/settings.json`
- Container restarts automatically when toggled
- Allows users to temporarily enable internet for model downloads
- IPC handlers: `settings:getOfflineMode`, `settings:setOfflineMode`
- Files: `electron/main.js:451-518`, `electron/splash.html`

**3. Comprehensive Logging System**
- Rotating JSON logs with 10 MB max, keeps 3 files
- Location: `~/.config/Silent Scribe/logs/silent-scribe-YYYY-MM-DD.log`
- Methods: `debug()`, `info()`, `warn()`, `error()`, `docker()`
- UI displays log path with "Open Folder" button
- Files: `electron/logger.js`, integrated throughout `main.js`

**4. Model Management UI**
- Tabbed interface for downloading/deleting models at runtime
- Download progress tracking via polling
- Shows model sizes, installation status
- Backend: `app/backend/model_manager.py`, endpoints in `main.py:328-390`

**5. GitHub Actions CI/CD**
- Builds for Linux (AppImage, deb), macOS (dmg), Windows (exe)
- Fixed GHCR authentication and package permissions
- Bundles Docker image in Electron installers
- Workflow: `.github/workflows/build.yml`

### Current Status 🟡

**Branch**: `feat/tabbed-ui-models-management`

**Waiting for**: GitHub Actions build to complete (triggered 2025-10-27 12:08 UTC)

**Expected artifacts**:
- `Silent Scribe-0.1.0-linux-x86_64.AppImage` (~3 GB)
- `Silent Scribe-0.1.0-linux-amd64.deb` (~3 GB)
- `Silent Scribe-0.1.0-mac-arm64.dmg` (~3 GB)
- `Silent Scribe-0.1.0-win-x64.exe` (~3 GB)

### Known Issues / Limitations ⚠️

1. **Docker container logs not captured**: Logs from inside container (model downloads, transcriptions) aren't automatically captured to Electron log files
2. **RPM packaging**: Only .deb and AppImage for Linux; no native .rpm yet (AppImage works on Fedora)
3. **Model download progress UI**: Backend logs progress but UI doesn't display real-time progress bar
4. **Large installer size**: Even with lite image (2.73 GB), installers are ~3 GB each

### Future Work (from todo.txt) 📋

1. **Proper logging**: Full container log capture to Electron logging system
2. **Ask questions based on context**: AI-powered Q&A on transcripts
3. **Tag items together**: Group related transcripts/summaries
4. **Ask questions based on group or all**: Query across multiple transcripts

### Testing Checklist (When Build Completes)

1. Download AppImage from GitHub Actions artifacts
2. Test on Fedora: `chmod +x *.AppImage && ./Silent\ Scribe-*.AppImage`
3. Verify:
   - App launches, splash screen appears
   - Docker image loads from bundle
   - Container starts successfully
   - Default: Air-gapped mode ON
   - Toggle offline mode OFF → container restarts
   - Download `base` model (should work with offline mode off)
   - Toggle back ON → container restarts again
   - Settings persist across app restarts
   - Log file created in `~/.config/Silent Scribe/logs/`
   - "Open Folder" button works
   - Logs contain all operations

### Next Steps

1. Test the AppImage build once GitHub Actions completes
2. Verify offline mode toggle works end-to-end
3. Test model downloads with offline mode disabled
4. Check logs are being written properly
5. Consider merging `feat/tabbed-ui-models-management` to main
6. Tag a release (e.g., `v0.1.0`) for distributable packages

**Resume commands**:
```bash
cd ~/Programming/silent-scribe
git status
gh run list --workflow build.yml --limit 5
gh run view <RUN_ID>  # Check build status
gh run download <RUN_ID> -D ./dist  # Download artifacts when complete
```
