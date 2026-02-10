# ============================================================================
# Second Brain — APP IMAGE (fast builds, ~2 minutes)
# Uses pre-built base image with all heavy dependencies
# ============================================================================
FROM europe-west1-docker.pkg.dev/gen-lang-client-0376839322/second-brain-eu/second-brain-base:latest

WORKDIR /app

# ── Application code only (this is the only thing that changes per deploy) ───
COPY . .

# Build metadata
RUN echo "v$(cat VERSION) — $(date -u +%Y-%m-%dT%H:%M:%SZ)" > .last_commit || true

# ── Health check ─────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# ── Start ────────────────────────────────────────────────────────────────────
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
