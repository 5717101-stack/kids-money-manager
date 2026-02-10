#!/bin/bash
# ============================================================================
# Deploy Second Brain to Cloud Run with GPU
# Uses pre-built base image → builds in ~2 minutes
# 
# Usage:
#   ./deploy-cloudrun.sh          — fast deploy (app code only)
#   ./deploy-cloudrun.sh --base   — rebuild base image (when requirements.txt changes)
# ============================================================================
set -e

PROJECT_ID="gen-lang-client-0376839322"
REGION="europe-west1"
SERVICE_NAME="second-brain"
REPO="second-brain-eu"
IMAGE_NAME="second-brain"
BASE_IMAGE="europe-west1-docker.pkg.dev/${PROJECT_ID}/${REPO}/second-brain-base:latest"

# Read version
VERSION=$(cat VERSION | tr -d '[:space:]')
IMAGE_TAG="europe-west1-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE_NAME}:v${VERSION}"

# ── Base image rebuild (rare) ────────────────────────────────────────────────
if [ "$1" = "--base" ]; then
    echo "============================================"
    echo "🏗️  Rebuilding BASE image (heavy deps)"
    echo "   This takes ~25 minutes"
    echo "   Only needed when requirements.txt changes"
    echo "============================================"
    
    gcloud builds submit . \
        --config=/dev/stdin \
        --region=${REGION} \
        --timeout=2400 <<CLOUDBUILD
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-f', 'Dockerfile.base', '-t', '${BASE_IMAGE}', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '${BASE_IMAGE}']
CLOUDBUILD
    
    echo ""
    echo "✅ Base image rebuilt: ${BASE_IMAGE}"
    echo "   Now run: ./deploy-cloudrun.sh"
    exit 0
fi

# ── Fast app deploy (~2 minutes) ────────────────────────────────────────────
echo "============================================"
echo "🚀 Fast Deploy — Second Brain v${VERSION}"
echo "   Image: ${IMAGE_TAG}"
echo "   Base:  ${BASE_IMAGE}"
echo "   Region: ${REGION} | GPU: NVIDIA L4"
echo "============================================"

# Step 1: Build app image (FROM base = fast, code only)
echo ""
echo "📦 Building app image (code changes only)..."
START_TIME=$(date +%s)

gcloud builds submit . \
    --tag="${IMAGE_TAG}" \
    --region=${REGION} \
    --timeout=600

BUILD_TIME=$(($(date +%s) - START_TIME))
echo "⏱️  Build completed in ${BUILD_TIME}s"

# Step 2: Deploy to Cloud Run
echo ""
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image="${IMAGE_TAG}" \
    --region=${REGION} \
    --platform=managed \
    --gpu=1 \
    --gpu-type=nvidia-l4 \
    --cpu=4 \
    --memory=16Gi \
    --min-instances=1 \
    --max-instances=2 \
    --timeout=3600 \
    --port=8080 \
    --no-cpu-throttling \
    --allow-unauthenticated

TOTAL_TIME=$(($(date +%s) - START_TIME))
echo ""
echo "============================================"
echo "✅ Deployed v${VERSION} in ${TOTAL_TIME}s!"
echo "   URL: https://second-brain-gajsewyeca-ew.a.run.app"
echo "============================================"
