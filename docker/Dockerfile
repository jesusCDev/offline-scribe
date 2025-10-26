# Multi-stage Dockerfile for Silent Scribe - Air-gapped Video Transcription
# This builds a complete image with all models and dependencies bundled

# Stage 1: Base builder with system dependencies
FROM python:3.11-slim AS base-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    ffmpeg \
    libavcodec-dev \
    libavformat-dev \
    libavdevice-dev \
    libavutil-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    libsndfile1 \
    libopenblas-dev \
    pkg-config \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Stage 2: Build whisper.cpp
FROM base-builder AS whispercpp-builder

WORKDIR /opt
RUN git clone --depth=1 --branch=v1.5.4 https://github.com/ggerganov/whisper.cpp.git && \
    cd whisper.cpp && \
    make -j$(nproc)

# Stage 2.5: Build llama.cpp
FROM base-builder AS llamacpp-builder

WORKDIR /opt
RUN git clone --depth=1 --branch=b3864 https://github.com/ggerganov/llama.cpp.git && \
    cd llama.cpp && \
    cmake -B build -S . -DLLAMA_OPENBLAS=ON -DCMAKE_BUILD_TYPE=Release && \
    cmake --build build --config Release -j$(nproc) && \
    mkdir -p /usr/local/bin/llama && \
    cp build/bin/llama-cli /usr/local/bin/llama/llama-cli 2>/dev/null || cp build/bin/main /usr/local/bin/llama/llama-cli

# Stage 3: Fetch only tiny model by default (users can download more at runtime)
FROM base-builder AS model-fetcher

# Copy model fetch script
COPY scripts/fetch_models.py /tmp/fetch_models.py

# Set environment for model downloads
ENV HF_HOME=/tmp/hf_cache
RUN mkdir -p /opt/models

# Copy local models if they exist (will be empty if not present)
COPY resources/models /opt/models_local

# Accept HF_TOKEN as build arg for pyannote model download
ARG HF_TOKEN
ENV HF_TOKEN=${HF_TOKEN}

# Cache busting arg to force rebuild when needed
ARG CACHEBUST=1

# Only fetch tiny model by default to keep image small
# Users can download additional models via the app's model management UI
RUN cp -r /opt/models_local/* /opt/models/ 2>/dev/null || true && \
    python3 /tmp/fetch_models.py --models tiny --skip-existing

# Stage 4: Final runtime image
FROM python:3.11-slim

# Version metadata (passed as build arg)
ARG IMAGE_VERSION=0.1.0
ARG BUILD_DATE
LABEL org.opencontainers.image.version="${IMAGE_VERSION}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.title="Silent Scribe"
LABEL org.opencontainers.image.description="Air-gapped video transcription with Whisper and Llama"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libopenblas0 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from base-builder
COPY --from=base-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=base-builder /usr/local/bin /usr/local/bin

# Copy whisper.cpp binary
COPY --from=whispercpp-builder /opt/whisper.cpp/main /opt/whisper.cpp/main

# Copy llama.cpp binary and libraries
COPY --from=llamacpp-builder /usr/local/bin/llama/llama-cli /usr/local/bin/llama/llama-cli
COPY --from=llamacpp-builder /opt/llama.cpp/build/src/libllama.so /usr/local/lib/libllama.so
COPY --from=llamacpp-builder /opt/llama.cpp/build/ggml/src/libggml.so /usr/local/lib/libggml.so
RUN ldconfig

# Copy all pre-downloaded models
COPY --from=model-fetcher /opt/models /opt/models

# Copy application code
COPY app /app
COPY .env.example /.env

# Copy fetch script to /tmp for runtime model downloads
COPY scripts/fetch_models.py /tmp/fetch_models.py

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /data/uploads /data/results && \
    chown -R appuser:appuser /data /app /opt/models

# Set environment variables for offline mode
ENV HF_HUB_OFFLINE=1
ENV TRANSFORMERS_OFFLINE=1
ENV HF_HOME=/opt/hf
ENV PYTHONUNBUFFERED=1
ENV NO_PROXY=*

# Data volume
VOLUME /data

# Expose port
EXPOSE 7860

# Switch to non-root user
USER appuser

WORKDIR /app

# Run application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
