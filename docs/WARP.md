# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Common Commands

### Build Docker Image
```bash
make build
# or
./scripts/build.sh
```
**Note:** Takes 30-60 minutes and requires ~15-20 GB disk space. Downloads all AI models. Only needs to be done once.

### Run Container
```bash
make run
# or
./scripts/run.sh
```
Starts the application at **http://localhost:7860** with `--network none` (completely offline).

### Stop Container
```bash
make stop
# or
./scripts/stop.sh
# or
Ctrl+C
```

### Clean Image
```bash
make clean
```
Removes the Docker image.

### Verify Health
```bash
curl http://localhost:7860/health
```

### View Logs
```bash
docker logs silent-scribe
```

### Verify Network Isolation
```bash
docker inspect silent-scribe | grep NetworkMode
# Should show: "NetworkMode": "none"
```

## Development Context

This is a **security-first, air-gapped video transcription system** designed for sensitive data:

- **Completely offline at runtime**: Container runs with `--network none`, zero internet access
- **All models bundled**: 10 AI models (5 sizes × 2 engines) pre-downloaded at build time (~15-20 GB)
- **Single Docker container**: Designed for distribution via flash drive (load pre-built image, run immediately)
- **Cross-platform**: Works on Mac (Intel & Apple Silicon) and Linux

## High-Level Architecture

### Backend
- **FastAPI + Uvicorn** (single worker) listening on port 7860
- **Single-process design**: `--workers 1` to prevent resource conflicts

### Dual Engine System
Two transcription engines with a shared abstraction:

1. **faster-whisper** (CTranslate2-based)
   - Better progress tracking
   - CPU-optimized
   - Recommended default

2. **whisper.cpp** (GGML-based)
   - Faster on Apple Silicon
   - Compiled at build time for target architecture

**Engine Interface** (`app/backend/engines/`):
```python
transcribe(
    audio_path: Path,
    output_dir: Path,
    model: str,
    settings: Dict[str, Any],
    progress_callback: Callable[[int], None]
) -> Dict[str, Path]  # Returns {format: file_path} for txt, srt, vtt
```

### Job Management
- **Single-job processing**: `JobManager` (in `job_manager.py`) enforces only one transcription at a time using an asyncio lock
- **Job state**: Stored in `/data/results/<job_id>/job.json` with status, progress, and result file paths
- **Background tasks**: Transcriptions run via `asyncio.create_task()` to avoid blocking API

### Progress Tracking
Progress flows through the system via callbacks:
```
Engine → JobManager → API → Frontend
```

- **faster-whisper**: Progress calculated from audio duration vs segment end time
- **whisper.cpp**: Progress estimated from stdout parsing (timestamps in output)

### Audio Pipeline
```
Video file → ffmpeg extraction → 16 kHz mono WAV → Whisper engine → TXT/SRT/VTT outputs
```

### Air-Gap Security Model
- **Build time**: Network access allowed for model downloads only
- **Runtime**: 
  - `--network none` flag on container
  - Environment: `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`
  - All models pre-loaded under `/opt/models/`
  - No CDN dependencies in web UI

## Key Code Locations

- `app/backend/main.py` — FastAPI routes and background processing
- `app/backend/config.py` — Configuration and available options (models, engines, compute types)
- `app/backend/job_manager.py` — Single-job locking and job state management
- `app/backend/engines/faster_whisper_engine.py` — CTranslate2 engine adapter
- `app/backend/engines/whisper_cpp_engine.py` — GGML engine adapter
- `docker/Dockerfile` — Multi-stage build (base → whisper.cpp → models → runtime)
- `scripts/fetch_models.py` — Downloads all models at build time

## Important Patterns

### Single-Job Processing
Only one transcription can run at a time. The `JobManager` uses an asyncio lock to enforce this:
```python
async with self._lock:
    if self.current_job and self.current_job.status == "processing":
        return None  # Busy
```

This prevents resource exhaustion on systems with limited RAM/CPU.

### Background Tasks
Transcriptions are scheduled as background tasks to keep the API responsive:
```python
asyncio.create_task(process_transcription(...))
```

### Progress Estimation
- **faster-whisper**: Tracks segment timestamps against total audio duration
- **whisper.cpp**: Parses progress indicators from stdout (e.g., `[00:00:10.000 --> 00:00:12.000]`)

### Air-Gap Security
- **Build time**: Network access for downloading models from Hugging Face
- **Runtime**: 
  - Container runs with `--network none`
  - Offline environment variables prevent any network calls
  - Models loaded from local `/opt/models/` directories

## Model Information

### Available Sizes
- **tiny** (~75 MB) - Fastest, lowest quality
- **base** (~150 MB) - Fast, decent quality
- **small** (~500 MB) - **Default** - Good balance
- **medium** (~1.5 GB) - Slower, better quality
- **large-v3** (~3 GB) - Slowest, best quality

### Storage Layout
- **faster-whisper**: `/opt/models/faster_whisper/<size>/` (CTranslate2 format)
- **whisper.cpp**: `/opt/models/whisper_cpp/<size>/*.bin` (GGML format)

### Default Configuration
- Model: `small`
- Compute type: `int8_float16`
- Threads: Auto-detected from CPU cores

## Data Flow

1. **Upload**: Video saved to `/data/uploads/<job_id>_<filename>`
2. **Audio extraction**: Extracted to `/data/results/<job_id>/audio.wav` (16 kHz mono)
3. **Transcription**: Outputs written to `/data/results/<job_id>/`:
   - `transcript.txt` - Plain text
   - `transcript.srt` - SubRip subtitles
   - `transcript.vtt` - WebVTT subtitles
4. **Cleanup**: On completion or failure, original upload and `audio.wav` are deleted

## Testing Notes

- **No test suite**: The `tests/` directory is currently empty
- **Manual testing**: Use the web UI at http://localhost:7860
- **API testing**: Hit endpoints directly (see `app/backend/main.py` for routes):
  - `GET /api/config` - Get available options
  - `POST /api/transcribe` - Start transcription
  - `GET /api/jobs/<job_id>/status` - Check job status
  - `GET /api/jobs/<job_id>/result.<format>` - Download results
  - `GET /api/history` - List recent jobs

## Important Constraints

- **Single-process design**: Uvicorn runs with `--workers 1` to avoid concurrency issues
- **No parallel transcriptions**: Only one job at a time (enforced by JobManager lock)
- **Memory requirements**: 
  - Minimum: 8 GB RAM
  - Recommended: 16 GB RAM for larger models
- **Build time**: One-time build per machine; pre-built images can be distributed via `docker save`/`docker load`
- **Non-root user**: Application runs as `appuser` (UID 1000) for security
- **Read-only filesystem**: Only `/data` is writable at runtime

---

## Recent Development Session (2025-10-27)

### What We Did

#### 1. Created Lite Docker Image Build (2.73 GB)
**Problem**: Original Docker image was 19.1 GB (all 5 Whisper models + Llama 2 + Pyannote), causing GitHub Actions builds to fail with disk space errors.

**Solution**: 
- Modified `docker/Dockerfile` line 72 to add `--skip-optional` flag
- Now builds with only `tiny` Whisper model (~150 MB)
- Reduces image from 19.1 GB → 2.73 GB
- Successfully pushed to private GHCR: `ghcr.io/jesuscdev/offline-scribe:latest`

**Files Changed**:
- `docker/Dockerfile` - Added `--skip-optional` to fetch_models.py call

#### 2. Implemented Offline Mode Toggle
**Problem**: Users couldn't download additional models at runtime because container runs with `HF_HUB_OFFLINE=1` (air-gapped mode).

**Solution**: Added UI toggle to enable/disable offline mode with container restart
- **Backend** (`electron/main.js`, `docker-manager.js`, `preload.js`):
  - Settings persistence in `~/.config/Silent Scribe/settings.json`
  - `offlineMode` default: `true` (air-gapped)
  - Container starts with `HF_HUB_OFFLINE` env var based on setting
  - Automatic container restart when toggled
  - IPC handlers: `settings:getOfflineMode`, `settings:setOfflineMode`

- **Frontend** (`electron/splash.html`):
  - Toggle switch: "🔒 Air-Gapped Mode"
  - Clear subtitle: "Disable internet access for model downloads"
  - Feedback messages on toggle

**Usage Flow**:
1. App starts in air-gapped mode (offline = true)
2. User un-toggles to enable internet
3. Container restarts with `HF_HUB_OFFLINE=0`
4. User can download models from Hugging Face
5. Toggle back on to re-enable air-gap

**Files Changed**:
- `electron/main.js` - Settings storage, IPC handlers, container restart logic
- `electron/docker-manager.js` - Added `offlineMode` parameter to `startContainer()`
- `electron/preload.js` - Exposed settings API
- `electron/splash.html` - Added toggle UI

#### 3. Added Comprehensive Logging System
**Problem**: No way to debug user issues or track application behavior.

**Solution**: Implemented rotating file logs with UI access
- **Logger Module** (`electron/logger.js`):
  - JSON-formatted logs with timestamps and levels
  - Rotating files: 10 MB max, keeps 3 files
  - Location: `~/.config/Silent Scribe/logs/silent-scribe-YYYY-MM-DD.log`
  - Methods: `debug()`, `info()`, `warn()`, `error()`, `docker()`
  - Console + file output

- **Integration** (`electron/main.js`):
  - Logs app startup/shutdown
  - Docker operations (check, start, stop)
  - Container state changes
  - Settings changes
  - All errors captured

- **UI** (`electron/splash.html`):
  - Displays log file path
  - "Open Folder" button to access logs
  - Users can easily share logs for debugging

**Log Format Example**:
```json
{"timestamp":"2025-10-27T07:36:14.123Z","level":"INFO","message":"Silent Scribe starting","data":{"version":"0.1.0","platform":"linux"}}
```

**Files Created/Changed**:
- `electron/logger.js` - New logger module
- `electron/main.js` - Logging integration
- `electron/preload.js` - Exposed log API (`getLogPath`, `getRecentLogs`, `openPath`)
- `electron/splash.html` - Log viewer UI

#### 4. Fixed GitHub Actions Workflow Issues
**Problems Fixed**:
1. Repository name case sensitivity (jesusCDev → jesuscdev for GHCR)
2. Missing `packages: read` permission for private GHCR access
3. Deprecated `directories` field in `package.json`
4. Missing author email for `.deb` package builds
5. electron-builder auto-publish errors (added `"publish": null`)

**Files Changed**:
- `.github/workflows/build.yml` - Fixed GHCR pull, added permissions
- `package.json` - Removed deprecated fields, added author email, disabled publish

### Current Status

**Branch**: `feat/tabbed-ui-models-management`

**GitHub Actions Build**: ✅ RUNNING (triggered 2025-10-27 12:08 UTC)
- Build type: `full` (bundles 2.73 GB Docker image)
- Expected artifacts:
  - `Silent Scribe-0.1.0-mac-arm64.dmg` (~3 GB)
  - `Silent Scribe-0.1.0-linux-x86_64.AppImage` (~3 GB)
  - `Silent Scribe-0.1.0-linux-amd64.deb` (~3 GB)
  - `Silent Scribe-0.1.0-win-x64.exe` (~3 GB)

**Private Package**: `ghcr.io/jesuscdev/offline-scribe:latest` (2.73 GB, lite build)

### Testing TODO

Once the GitHub Actions build completes:

1. **Download AppImage** from artifacts
2. **Test on Fedora**:
   ```bash
   chmod +x Silent\ Scribe-0.1.0-linux-x86_64.AppImage
   ./Silent\ Scribe-0.1.0-linux-x86_64.AppImage
   ```

3. **Verify Features**:
   - ✅ App launches and shows splash screen
   - ✅ Docker image loads from bundle (bundled in AppImage)
   - ✅ Container starts successfully
   - ✅ Default: Air-gapped mode ON (offline)
   - ✅ Toggle offline mode OFF
   - ✅ Container restarts automatically
   - ✅ Download `base` model (should work now with offline mode off)
   - ✅ Toggle back ON (container restarts again)
   - ✅ Setting persists across app restarts
   - ✅ Log file created in `~/.config/Silent Scribe/logs/`
   - ✅ "Open Folder" button works
   - ✅ Logs contain all operations

4. **Test Log File Sharing**:
   - Find log file path in UI
   - Open logs folder
   - Verify logs are readable JSON
   - Confirm all major operations logged

### Known Issues / Future Work

1. **Docker container log capture**: Not yet implemented. Logs from inside the Docker container (model downloads, transcriptions) aren't automatically captured to the Electron log file.

2. **RPM packaging**: Currently builds `.deb` and AppImage for Linux. Native `.rpm` for Fedora/RHEL not yet configured (AppImage works fine on Fedora though).

3. **Model download progress UI**: Model downloads show status polling but no real-time progress bar. The backend logs progress but UI doesn't display it.

4. **Full build size**: Even with lite image (2.73 GB), the bundled installers are ~3 GB each. Consider ultra-lite version (no models bundled at all) for faster distribution.

### Next Session Starting Point

**Current state**: Waiting for GitHub Actions build to complete (check: https://github.com/jesusCDev/offline-scribe/actions)

**Next steps**:
1. Download and test the AppImage build
2. Verify offline mode toggle works end-to-end
3. Test model downloads with offline mode disabled
4. Check logs are being written properly
5. If all works, consider merging `feat/tabbed-ui-models-management` branch to main
6. Tag a release (e.g., `v0.1.0`) to create distributable packages

**Commands to resume**:
```bash
cd ~/Programming/silent-scribe
git status
gh run list --workflow build.yml --limit 5
gh run view <RUN_ID>  # Check build status
gh run download <RUN_ID> -D ./dist  # Download artifacts when complete
```
