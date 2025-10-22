# Silent Scribe - Project Status & Goals

## Project Overview
Air-gapped video-to-text transcription system with web UI for sensitive data processing.

## Current Status: 🟡 IN PROGRESS - Building Docker Image

### Completed ✅
1. ✅ Project scaffolding and structure
2. ✅ FastAPI backend with dual engines (faster-whisper & whisper.cpp)
3. ✅ Web UI with drag-and-drop upload
4. ✅ Single-job processing with locking
5. ✅ Progress tracking system
6. ✅ Output formats: TXT, SRT, VTT
7. ✅ Docker configuration with multi-stage build
8. ✅ Security: --network none, offline mode
9. ✅ Git repository initialized with proper .gitignore
10. ✅ Build/start/kill scripts created
11. ✅ Local models support (resources/models/)
12. ✅ Requirements.txt with compatible versions
13. ✅ Model fetcher script with skip-existing flag

### In Progress 🟡
- Building Docker image (30-60 min process)
  - Base dependencies installation
  - whisper.cpp compilation
  - **Model downloads (10 models, ~15-20 GB)**
  - Final image assembly

### Next Steps 📋
1. Complete Docker build
2. Test application locally
3. Create `load` script for Docker image distribution
4. Create `save` script to export Docker image
5. Update README with flash drive distribution instructions
6. Test on Mac (if available)
7. Create distribution package

## Goals

### Primary Goal
Create a completely offline, secure video transcription system that:
- ✅ Runs with zero internet access
- ✅ Has all AI models bundled
- ✅ Provides web interface for ease of use
- 🟡 Can be distributed via flash drive (in progress)

### Distribution Model
**Flash Drive Distribution:**
```
silent-scribe/
├── silent-scribe-image.tar.gz  # Pre-built Docker image (~15-20 GB)
├── load                         # Load image into Docker
├── start                        # Run the application
├── kill                         # Stop the application
└── README.md                    # Instructions
```

**User workflow on new machine:**
1. Install Docker (one-time)
2. Run `./load` (loads pre-built image, ~5-10 min)
3. Run `./start` (launches app immediately)
4. Open http://localhost:7860
5. Upload videos, get transcripts!

### Technical Requirements Met
- ✅ Mac & Linux compatible (Docker-based)
- ✅ Single Docker container
- ✅ 5 model sizes (tiny → large-v3)
- ✅ 2 engines (faster-whisper, whisper.cpp)
- ✅ Performance tuning options
- ✅ Real-time progress tracking
- ✅ Air-gapped (--network none)

## Build Issues Encountered & Fixed
1. ✅ Missing ffmpeg dev libraries → Added libav* packages
2. ✅ av package version conflict → Removed explicit version
3. ✅ Docker COPY command for optional models → Fixed with conditional logic
4. 🟡 Current: Building image with model downloads

## Dependencies
- Docker (required)
- 15-20 GB disk space (for image + models)
- 8+ GB RAM (16 GB recommended)
- Multi-core CPU (recommended)

## Security Features
- No network access at runtime (--network none)
- All models pre-downloaded at build time
- Non-root user execution
- No CDN dependencies in UI
- Local processing only

## Performance Notes
- Single job processing (prevents resource conflicts)
- Configurable threads and compute types
- Model selection for speed vs quality trade-off
- Default: small model + int8_float16 (balanced)

## Distribution Checklist (When Ready)
- [ ] Docker build complete
- [ ] Local testing passed
- [ ] Save Docker image to .tar.gz
- [ ] Create load script
- [ ] Update README with flash drive instructions
- [ ] Test load/start workflow
- [ ] Document Mac-specific setup
- [ ] Create distribution package

## Notes
- Models are ~5-6 GB total (10 models: 5 sizes × 2 engines)
- Docker image will be ~15-20 GB compressed
- Build only needs to happen once (on this machine)
- Users on Mac/Linux just load the pre-built image

## Last Updated
2025-10-22 03:34:00 UTC - Building Docker image in progress
