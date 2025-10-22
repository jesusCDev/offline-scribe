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

# Stage 3: Fetch all models (or use local if available)
FROM base-builder AS model-fetcher

# Copy model fetch script
COPY scripts/fetch_models.py /tmp/fetch_models.py

# Set environment for model downloads
ENV HF_HOME=/tmp/hf_cache
RUN mkdir -p /opt/models

# Copy local models if they exist (build context aware)
COPY resources/models/ /opt/models/ 2>/dev/null || true

# Fetch missing models (this requires network access at build time if models not local)
RUN python3 /tmp/fetch_models.py --skip-existing

# Stage 4: Final runtime image
FROM python:3.11-slim

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

# Copy all pre-downloaded models
COPY --from=model-fetcher /opt/models /opt/models

# Copy application code
COPY app /app
COPY .env.example /.env

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /data/uploads /data/results && \
    chown -R appuser:appuser /data /app

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
