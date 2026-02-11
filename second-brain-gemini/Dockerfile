# ============================================================================
# Second Brain — APP IMAGE (fast builds, ~3-5 minutes)
# Uses pre-built base image with all heavy dependencies
# ============================================================================
FROM europe-west1-docker.pkg.dev/gen-lang-client-0376839322/second-brain-eu/second-brain-base:latest

WORKDIR /app

# ── Pre-download pyannote models (avoids HuggingFace 429 rate limits) ────────
# Models are cached in the image so no runtime downloads are needed.
# Pass HF_TOKEN as build arg: --build-arg HF_TOKEN=hf_xxx
ARG HF_TOKEN=""
ENV HF_HOME=/app/.hf_cache
RUN if [ -n "$HF_TOKEN" ]; then \
    echo "📥 Pre-downloading pyannote models..." && \
    python -c "\
import os; os.environ['HF_TOKEN']='${HF_TOKEN}'; \
from huggingface_hub import snapshot_download; \
print('  → pyannote/speaker-diarization-3.1'); \
snapshot_download('pyannote/speaker-diarization-3.1', token='${HF_TOKEN}'); \
print('  → pyannote/wespeaker-voxceleb-resnet34-LM'); \
snapshot_download('pyannote/wespeaker-voxceleb-resnet34-LM', token='${HF_TOKEN}'); \
print('✅ Models cached in /app/.hf_cache') \
" && echo "✅ pyannote models embedded in image" ; \
    else echo "⚠️ HF_TOKEN not provided — pyannote models not pre-cached"; fi

# ── Application code only (this is the only thing that changes per deploy) ───
COPY . .

# Build metadata
RUN echo "v$(cat VERSION) — $(date -u +%Y-%m-%dT%H:%M:%SZ)" > .last_commit || true

# ── Health check ─────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# ── Start ────────────────────────────────────────────────────────────────────
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
