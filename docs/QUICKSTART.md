# 🚀 Silent Scribe - Quick Start Guide

Get up and running with air-gapped video transcription in 3 steps.

## Prerequisites

- **Docker** installed ([Get Docker](https://docs.docker.com/get-docker/))
- **15-20 GB** free disk space
- **8+ GB RAM** (16 GB recommended)

## Step 1: Build the Image (First Time Only)

This step downloads and bundles all AI models. Takes 30-60 minutes.

```bash
cd silent-scribe
make build
```

Or:

```bash
./scripts/build.sh
```

**What's happening?**
- Compiling whisper.cpp for your CPU
- Downloading 10 AI models (5 sizes × 2 engines)
- Bundling everything into one Docker image
- **This only needs to be done once!**

## Step 2: Run the Application

```bash
make run
```

Or:

```bash
./scripts/run.sh
```

The application starts at: **http://localhost:7860**

## Step 3: Transcribe Videos

1. Open **http://localhost:7860** in your browser
2. **Drag & drop** a video file or click to browse
3. Choose settings:
   - **Engine**: faster-whisper (recommended)
   - **Model**: small (best balance)
   - **Threads**: Match your CPU cores
4. Click **"Start Transcription"**
5. Wait for progress to complete
6. Download your transcripts (TXT, SRT, VTT)

## Stop the Application

**Just press Ctrl+C** - the container will automatically stop and clean up!

Or run:
```bash
make stop
# or: ./scripts/stop.sh
```

✅ **No worries about orphaned containers** - `run.sh` automatically detects and removes any leftover containers before starting.

---

## Tips for Best Results

### For Speed 🚀
- Use **tiny** or **base** model
- Choose **faster-whisper** engine
- Set compute type to **int8**

### For Quality 🎯
- Use **medium** or **large-v3** model
- Choose **whisper.cpp** on Apple Silicon
- Set compute type to **int8_float16** or **float32**

### For Balance ⚖️
- Use **small** model ✅
- Choose **faster-whisper** engine ✅
- Set compute type to **int8_float16** ✅
- Threads = your CPU cores ✅

---

## Common Issues

### Build fails
```bash
# Retry - sometimes it's just a network hiccup
make build
```

### "Port already in use" error

**This shouldn't happen!** The scripts auto-cleanup. But if it does:
```bash
./scripts/stop.sh   # Force cleanup
./scripts/run.sh    # Try again
```

Still stuck? Check what's using the port:
```bash
lsof -i :7860
# or
sudo netstat -tlnp | grep 7860
```

### Out of memory during transcription
- Use a smaller model (tiny, base, or small)
- Reduce threads
- Increase Docker memory limit (Docker Desktop → Settings → Resources)

---

## Next Steps

- Read the full [README.md](README.md) for advanced usage
- Check out the [original spec](air_gapped_mac_transcription_with_docker_whisper.md)
- Experiment with different models and settings

**Remember**: This application is **100% offline** and runs with `--network none` for maximum security! 🔒
