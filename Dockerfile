# =============================================================================
# AI Secretary System - Multi-stage Docker Build
# Supports GPU mode (XTTS + vLLM) and CPU mode (Piper + Gemini)
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Build Vue.js Admin Panel
# -----------------------------------------------------------------------------
FROM node:20-alpine AS admin-builder

WORKDIR /build

# Copy package files first for better caching
COPY admin/package*.json ./
RUN npm ci --silent

# Copy source and build
COPY admin/ ./
RUN npm run build

# -----------------------------------------------------------------------------
# Stage 2: Python Runtime with CUDA support
# -----------------------------------------------------------------------------
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04 AS runtime

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    libportaudio2 \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.11 /usr/bin/python \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3

WORKDIR /app

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install PyTorch with CUDA support first (large dependency)
RUN pip install --no-cache-dir \
    torch==2.1.2 \
    torchaudio==2.1.2 \
    --index-url https://download.pytorch.org/whl/cu121

# Install remaining Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY *.py ./
COPY db/ ./db/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Scripts
COPY scripts/ ./scripts/

# Admin panel (from build stage)
COPY --from=admin-builder /build/dist ./admin/dist/

# Voice samples
COPY Гуля/ ./Гуля/
COPY Лидия/ ./Лидия/

# Web widget
COPY web-widget/ ./web-widget/

# Create directories for volumes
RUN mkdir -p /app/data /app/logs /app/models /app/temp /app/cache

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV ORCHESTRATOR_PORT=8002
ENV COQUI_TOS_AGREED=1
ENV TTS_CACHE_PATH=/root/.cache/tts_models

# Entrypoint script
COPY scripts/docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "orchestrator.py"]

# -----------------------------------------------------------------------------
# Stage 3: CPU-only variant (smaller image, no CUDA)
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS cpu

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libportaudio2 \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (CPU versions)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# Application code
COPY *.py ./
COPY db/ ./db/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY scripts/ ./scripts/

# Admin panel
COPY --from=admin-builder /build/dist ./admin/dist/

# Voice samples
COPY Гуля/ ./Гуля/
COPY Лидия/ ./Лидия/

# Web widget
COPY web-widget/ ./web-widget/

# Create directories
RUN mkdir -p /app/data /app/logs /app/models /app/temp /app/cache

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV ORCHESTRATOR_PORT=8002
ENV LLM_BACKEND=gemini

# Entrypoint
COPY scripts/docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "orchestrator.py"]
