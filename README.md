# 🤫 Silent Scribe - Air-Gapped Video Transcription

A completely offline, air-gapped video-to-text transcription system with a web interface. Designed for sensitive data that requires maximum security with zero internet access.

## ✨ Features

- 🔒 **Completely Air-Gapped** - Runs with `--network none`, zero internet access at runtime
- 🌐 **Web Interface** - Drag-and-drop video uploads with real-time progress
- 🚀 **Dual Engines** - Choose between faster-whisper (Python) or whisper.cpp (C++)
- 📦 **All Models Bundled** - Includes tiny, base, small, medium, and large-v3 models
- ⚙️ **Performance Tuning** - Adjust model size, compute type, threads, and more
- 📝 **Multiple Formats** - Outputs TXT, SRT, and VTT subtitle formats
- 💻 **Cross-Platform** - Works on Mac (Intel & Apple Silicon) and Linux

## 🏗️ Architecture

- **Backend**: FastAPI + Uvicorn
- **Engines**: 
  - faster-whisper (CTranslate2, CPU-optimized)
  - whisper.cpp (GGML, optimized for Apple Silicon)
- **Models**: 5 sizes × 2 engines = 10 model variants (multi-language)
- **Security**: No network access, non-root user, read-only filesystem (except /data)

## 📋 Requirements

- **Docker** (or Docker Desktop for Mac)
- **Disk Space**: ~15-20 GB for the image (all models included)
- **RAM**: 8 GB minimum, 16 GB recommended for larger models
- **CPU**: Multi-core recommended (single-process design)

## 🚀 Quick Start

### Installation

1. **Clone or navigate to the project**:
   ```bash
   cd silent-scribe
   ```

2. **Build the Docker image** (this downloads and bundles all models):
   ```bash
   make build
   # or
   ./scripts/build.sh
   ```
   
   ⚠️ **Note**: Building takes 30-60 minutes and requires ~15-20 GB disk space. This only needs to be done once.

3. **Run the container**:
   ```bash
   make run
   # or
   ./scripts/run.sh
   ```

4. **Open the web UI**:
   - Navigate to **http://localhost:7860** in your browser

### Usage

1. **Upload a Video**
   - Drag and drop a video file (MP4, MOV, MKV, AVI, etc.) or click to browse
   - Supports audio files too (WAV, MP3, etc.)

2. **Configure Settings**
   - **Engine**: faster-whisper (recommended) or whisper.cpp
   - **Model Size**: 
     - `tiny` - Fastest, lowest quality
     - `base` - Fast, decent quality
     - `small` - **Recommended** - Good balance
     - `medium` - Slower, better quality
     - `large-v3` - Slowest, best quality
   - **Compute Type** (faster-whisper only):
     - `int8` - Fastest, lower quality
     - `int8_float16` - **Recommended** - Good balance
     - `int16` - Higher quality
     - `float32` - Highest quality, slowest
   - **Threads**: Number of CPU cores to use
   - **Language**: Auto-detect or specify (en, es, fr, de, etc.)

3. **Start Transcription**
   - Click "Start Transcription"
   - Watch the progress bar
   - When complete, view the transcript and download TXT/SRT/VTT files

4. **Stop the Container**:
   ```bash
   make stop
   # or
   ./scripts/stop.sh
   ```

## 🔧 Advanced Usage

### Running Detached
```bash
docker run -d \
  -p 7860:7860 \
  -v "$(pwd)/data:/data" \
  --name silent-scribe \
  --network none \
  silent-scribe:latest
```

### Custom Port
```bash
docker run --rm -it \
  -p 8080:7860 \
  -v "$(pwd)/data:/data" \
  --name silent-scribe \
  --network none \
  silent-scribe:latest
```

### Accessing Results via CLI
```bash
# List results
ls -la data/results/

# View a transcript
cat data/results/<job-id>/transcript.txt
```

## 🔒 Security

This application is designed for maximum security with sensitive data:

- ✅ **No Network Access**: Container runs with `--network none`
- ✅ **All Models Bundled**: No runtime downloads, all models pre-downloaded at build time
- ✅ **Non-Root User**: Application runs as unprivileged user
- ✅ **Offline-First**: `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` environment variables set
- ✅ **No External Resources**: Web UI has no CDN dependencies, fonts, or external scripts
- ✅ **Local Processing Only**: All data stays on your machine

### Verifying Air-Gapped Operation

On Linux:
```bash
# Check network namespaces while container is running
docker inspect silent-scribe | grep NetworkMode
# Should show: "NetworkMode": "none"
```

On Mac:
```bash
# Container should not be able to resolve DNS
docker exec silent-scribe ping -c 1 google.com
# Should fail with "network unreachable"
```

## 📦 What's Included

### Models
- **faster-whisper** (CTranslate2 format):
  - tiny (~75 MB)
  - base (~150 MB)
  - small (~500 MB)
  - medium (~1.5 GB)
  - large-v3 (~3 GB)

- **whisper.cpp** (GGML format):
  - ggml-tiny.bin (~75 MB)
  - ggml-base.bin (~150 MB)
  - ggml-small.bin (~500 MB)
  - ggml-medium.bin (~1.5 GB)
  - ggml-large-v3.bin (~3 GB)

### Output Formats
- **TXT**: Plain text transcript
- **SRT**: SubRip subtitle format (for video players)
- **VTT**: WebVTT subtitle format (for web players)

## 🐛 Troubleshooting

### Build Issues

**Problem**: Build fails with "network timeout"
```bash
# Solution: Retry the build
make build
```

**Problem**: Out of disk space
```bash
# Solution: Clean up Docker
docker system prune -a
```

### Runtime Issues

**Problem**: Container won't start
```bash
# Check if port is in use
lsof -i :7860

# Use a different port
docker run -p 8080:7860 ... silent-scribe:latest
```

**Problem**: Transcription fails
- Check that the video file is valid (try playing it first)
- Try a smaller model (tiny or base)
- Check available RAM (`docker stats silent-scribe`)

**Problem**: Out of memory
- Use a smaller model (tiny, base, or small)
- Reduce threads setting
- Close other applications

### Mac-Specific Issues

**Problem**: Apple Silicon performance
- The image includes optimizations for both Intel and ARM
- whisper.cpp is particularly fast on Apple Silicon
- faster-whisper works well but is CPU-only

**Problem**: Docker Desktop memory limit
- Go to Docker Desktop → Settings → Resources
- Increase Memory to at least 8 GB (16 GB recommended)

### Linux-Specific Issues

**Problem**: Permission denied on /data
```bash
# Fix permissions
sudo chown -R $(id -u):$(id -g) data/
```

## 📊 Performance Tips

1. **Choose the Right Model**:
   - For speed: `tiny` or `base`
   - For quality: `medium` or `large-v3`
   - For balance: `small` ✅

2. **Optimize Threads**:
   - Set to number of CPU cores
   - Don't exceed physical cores

3. **Compute Type** (faster-whisper):
   - `int8_float16` is the best balance ✅
   - `int8` for maximum speed
   - `float32` for maximum quality

4. **Engine Choice**:
   - **faster-whisper**: Better progress tracking, more tunable
   - **whisper.cpp**: Faster on Apple Silicon

## 🗂️ Project Structure

```
silent-scribe/
├── app/
│   ├── backend/
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Configuration
│   │   ├── job_manager.py       # Job management
│   │   └── engines/
│   │       ├── faster_whisper_engine.py
│   │       └── whisper_cpp_engine.py
│   └── templates/
│       └── index.html           # Web UI
├── docker/
│   └── Dockerfile               # Multi-stage build
├── scripts/
│   ├── build.sh                 # Build script
│   ├── run.sh                   # Run script
│   ├── stop.sh                  # Stop script
│   └── fetch_models.py          # Model fetcher (build-time)
├── data/                        # Mounted volume
│   ├── uploads/                 # Uploaded videos
│   └── results/                 # Transcription results
├── requirements.txt             # Python dependencies
├── Makefile                     # Make shortcuts
└── README.md                    # This file
```

## 🤝 Contributing

This is a self-contained, air-gapped application. Modifications should maintain:
- Zero runtime network access
- All dependencies bundled at build time
- Security-first design

## 📜 License

This project uses the following open-source components:
- faster-whisper (MIT License)
- whisper.cpp (MIT License)
- FastAPI (MIT License)
- OpenAI Whisper models (MIT License)

## 🙏 Credits

Built on top of excellent open-source projects:
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) by Guillaume Klein
- [whisper.cpp](https://github.com/ggerganov/whisper.cpp) by Georgi Gerganov
- [OpenAI Whisper](https://github.com/openai/whisper) by OpenAI

---

**Silent Scribe** - Transcribing in silence, secure and offline. 🤫🔒
