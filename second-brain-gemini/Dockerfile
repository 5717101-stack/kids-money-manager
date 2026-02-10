# ============================================================================
# Second Brain — Cloud Run GPU Dockerfile
# Base: NVIDIA CUDA 12.2 + Python 3.11 + pyannote + torch (CUDA)
# GPU: NVIDIA L4 on Cloud Run
# ============================================================================
FROM nvidia/cuda:12.2.2-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# ── System dependencies ──────────────────────────────────────────────────────
RUN apt-get update -qq && \
    apt-get install -y -qq --no-install-recommends \
        software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa -y \
    && apt-get update -qq && \
    apt-get install -y -qq --no-install-recommends \
        python3.11 \
        python3.11-venv \
        python3.11-dev \
        python3.11-distutils \
        ffmpeg \
        fonts-dejavu-core \
        libsndfile1 \
        build-essential \
        curl \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Python setup ─────────────────────────────────────────────────────────────
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

WORKDIR /app

# ── Python dependencies (cached layer — changes rarely) ─────────────────────
COPY requirements.txt .

# Install PyTorch with CUDA 12.1 support FIRST (GPU-accelerated)
RUN pip install --no-cache-dir \
    torch==2.2.0+cu121 \
    torchaudio==2.2.0+cu121 \
    --index-url https://download.pytorch.org/whl/cu121

# Install remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code (changes frequently — last layer) ───────────────────────
COPY . .

# Build metadata
RUN echo "Cloud Run GPU Build $(date -u +%Y-%m-%dT%H:%M:%SZ)" > .last_commit || true

# ── Health check ─────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# ── Start ────────────────────────────────────────────────────────────────────
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
