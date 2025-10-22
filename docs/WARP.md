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
