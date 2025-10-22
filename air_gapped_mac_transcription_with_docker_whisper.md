# Goal (what you asked for)
Turn offline video recordings into text **on a Mac** with containers that:
- run with **no network access** (`--network none`),
- use **relative paths** so you can drop the folder on any machine,
- cover two engines:
  1) **whisper.cpp** (C/C++, fast on Apple Silicon)
  2) **faster‑whisper** + **whisper‑ctranslate2** (Python CLI)

You’ll get a repeatable project that mounts `./in`, `./out`, and `./models` into the container. Put videos in `./in/`, transcripts appear in `./out/`, and models live in `./models/`.

---

# Folder layout (relative paths)
Create a working folder anywhere (e.g., `~/stt/`). Inside it, keep this structure:

```
./in/                         # drop camera videos here (mp4/mov/mkv...)
./out/                        # transcripts land here (.txt, .srt, .vtt)
./models/                     # model files/folders kept locally
  ├─ ggml/                    # whisper.cpp models (e.g., ggml-base.en.bin)
  └─ ct2/                     # faster‑whisper CTranslate2 models (e.g., small)
./docker/
  ├─ whispercpp/
  │   └─ Dockerfile
  └─ faster-whisper/
      └─ Dockerfile
./scripts/
  ├─ transcribe_whispercpp.sh
  └─ transcribe_fasterwhisper.sh
```

> Tip: keep **models** outside the images so you can reuse them across machines and versions without rebuilding.

---

# One‑time setup (online, on any Mac)
1) **Install Docker Desktop for Mac**.
2) **Prefetch models** to `./models/` (so runtime never downloads anything):
   - whisper.cpp (ggml): place files like `./models/ggml/ggml-base.en.bin`
   - faster‑whisper (CT2): place a directory like `./models/ct2/small/` (contains `model.bin`, tokenizer, etc.)

3) **Build the images** (you can do this once online, then `docker save` / `docker load` the images to other machines):
   - whisper.cpp: `docker build -t local/whispercpp:latest ./docker/whispercpp`
   - faster‑whisper: `docker build -t local/fasterwhisper:latest ./docker/faster-whisper`

> To move images between machines:
> ```
> docker save local/whispercpp:latest > whispercpp.tar
> docker save local/fasterwhisper:latest > fasterwhisper.tar
> # on another Mac
> docker load < whispercpp.tar
> docker load < fasterwhisper.tar
> ```

---

# Dockerfiles (kept simple, Apple‑Silicon friendly)

## `./docker/whispercpp/Dockerfile`
```dockerfile
# Build whisper.cpp once in the image; include ffmpeg for audio conversion
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential cmake ffmpeg ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN git clone --depth=1 https://github.com/ggml-org/whisper.cpp.git && \
    cmake -S whisper.cpp -B build && cmake --build build -j --config Release

# Runtime layout
WORKDIR /work
ENV PATH="/opt/build/bin:$PATH"
# No model baked in; mount ./models/ggml at runtime
ENTRYPOINT ["bash", "-lc"]
```

## `./docker/faster-whisper/Dockerfile`
```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Install CLIs
RUN pip install --no-cache-dir faster-whisper whisper-ctranslate2

# Belt-and-suspenders: keep the runtime in offline mode
ENV HF_HUB_OFFLINE=1
WORKDIR /work
ENTRYPOINT ["bash", "-lc"]
```

> If you need to build **fully offline** later, pre‑download wheels into `./docker/faster-whisper/wheels/` and replace the `pip install` line with a local `--find-links` install. Keep models in `./models/ct2/...` so there’s no network access at run time.

---

# Helper scripts

## `./scripts/transcribe_whispercpp.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
IN_FILE="$1"                  # e.g., ./in/meeting1.mp4
MODEL_BIN="${2:-./models/ggml/ggml-base.en.bin}"
BASE="$(basename "${IN_FILE}")"
NAME="${BASE%.*}"

# Convert to 16 kHz, mono, 16-bit WAV (whisper-cli expects 16-bit WAV)
ffmpeg -y -i "$IN_FILE" -ar 16000 -ac 1 -c:a pcm_s16le "./out/${NAME}.wav"

# Transcribe → .txt + .srt + .vtt next to the WAV
whisper-cli -m "$MODEL_BIN" \
  -f "./out/${NAME}.wav" \
  -otxt -osrt -ovtt \
  -of "./out/${NAME}"

echo "Done: ./out/${NAME}.txt (and .srt/.vtt)"
```

## `./scripts/transcribe_fasterwhisper.sh`
```bash
#!/usr/bin/env bash
set -euo pipefail
IN_FILE="$1"                     # e.g., ./in/meeting1.mp4 or .wav
MODEL_DIR="${2:-./models/ct2/small}"  # CT2 model directory

# You can pass videos directly; faster-whisper decodes audio itself via PyAV,
# but converting to WAV first can help for consistency:
# ffmpeg -y -i "$IN_FILE" -ar 16000 -ac 1 -c:a pcm_s16le "./out/temp.wav" && IN_FILE="./out/temp.wav"

# Write text + srt/vtt into ./out
whisper-ctranslate2 "$IN_FILE" \
  --model_directory "$MODEL_DIR" \
  --output_dir ./out \
  --compute_type int8       # good default on CPU

echo "Done. See ./out for outputs."
```

> Make scripts executable: `chmod +x ./scripts/*.sh`

---

# Run: start/stop/kill & file flow
All commands are relative to **the project root** (where `./in`, `./out`, `./models` live).

## Option 1 — whisper.cpp (no network)
**Start a one‑off run:**
```bash
docker run --rm \
  --name whispercpp \
  --network none \
  -v "$(pwd)/in:/work/in" \
  -v "$(pwd)/out:/work/out" \
  -v "$(pwd)/models:/work/models" \
  local/whispercpp:latest \
  "./scripts/transcribe_whispercpp.sh ./in/<your_video>.mp4 ./models/ggml/ggml-base.en.bin"
```

**Stop/kill (if you ever run detached):**
```bash
docker stop whispercpp    # graceful
# or
docker kill whispercpp    # immediate
```

**Move data in/out:** just copy to `./in/` on the host; results appear in `./out/` automatically via the bind mount. No `docker cp` needed.

## Option 2 — faster‑whisper + whisper‑ctranslate2 (no network)
**Start a one‑off run:**
```bash
docker run --rm \
  --name fwhisper \
  --network none \
  -e HF_HUB_OFFLINE=1 \
  -v "$(pwd)/in:/work/in" \
  -v "$(pwd)/out:/work/out" \
  -v "$(pwd)/models:/work/models" \
  local/fasterwhisper:latest \
  "./scripts/transcribe_fasterwhisper.sh ./in/<your_video>.mp4 ./models/ct2/small"
```

**Stop/kill (if you ever run detached):**
```bash
docker stop fwhisper   # graceful
# or
docker kill fwhisper   # immediate
```

**Move data in/out:** same as above: use `./in` and `./out`.

---

# Verifying “air‑gapped” execution on macOS (optional)
If you want to double‑check, in another terminal run:
```
nettop -p "$(docker inspect --format '{{.State.Pid}}' whispercpp)"
```
You should see no external sockets while the container runs with `--network none`. (You can substitute `fwhisper` for the other container.)

---

# Notes & tweaks
- **Model choice**: `ggml-base.en.bin` (whisper.cpp) and `ct2/small` (faster‑whisper) are good starting points. Larger models are more accurate but heavier.
- **Speaker labels**: If you later want diarization, add it outside this air‑gapped run (it requires extra models). Keep transcripts local and process on a separate step.
- **Batching**: You can loop over files in `./in` by running the `docker run ...` line inside a shell `for` loop.
- **File formats**: whisper.cpp expects **16‑bit WAV**; the script converts for you. faster‑whisper can read common media types directly, but a WAV conversion keeps behavior consistent across engines.
- **Performance**: On Apple Silicon, whisper.cpp benefits from its native optimizations; faster‑whisper’s `--compute_type int8` is a solid CPU default. Try larger models later if you want higher quality.

---

# Quick checklist before first run
- [ ] `./in` has your video(s)
- [ ] `./models/ggml/ggml-*.bin` (for whisper.cpp)
- [ ] `./models/ct2/<size>/` (for faster‑whisper)
- [ ] Images built locally (`docker images | grep local/`)
- [ ] You’re using `--network none` in every `docker run`

That’s it—you now have repeatable, **no‑network**, Mac-friendly transcription with both engines. Drop new videos into `./in`, run either container, and collect clean `.txt/.srt/.vtt` in `./out`. Enjoy!

