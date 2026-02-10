#!/bin/bash
# ============================================================================
# Deploy Second Brain to Cloud Run with GPU
# Usage: ./deploy-cloudrun.sh
# ============================================================================
set -e

PROJECT_ID="gen-lang-client-0376839322"
REGION="europe-west1"
SERVICE_NAME="second-brain"
REPO="second-brain-eu"
IMAGE_NAME="second-brain"

# Read version
VERSION=$(cat VERSION | tr -d '[:space:]')
IMAGE_TAG="europe-west1-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE_NAME}:v${VERSION}"

echo "============================================"
echo "🚀 Deploying Second Brain v${VERSION}"
echo "   Image: ${IMAGE_TAG}"
echo "   Region: ${REGION}"
echo "   GPU: NVIDIA L4"
echo "============================================"

# Step 1: Build image via Cloud Build (uses Docker layer caching)
echo ""
echo "📦 Building container image..."
gcloud builds submit . \
    --tag="${IMAGE_TAG}" \
    --region=${REGION} \
    --timeout=1200

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

echo ""
echo "✅ Deployment complete!"
echo "   URL: https://second-brain-gajsewyeca-ew.a.run.app"
echo "   Version: v${VERSION}"
