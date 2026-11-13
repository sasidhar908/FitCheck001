#!/usr/bin/env bash
# Deploy the official Crawl4AI container to Google Cloud Run
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project)}"
REGION="${GCP_REGION:-asia-southeast1}"
SERVICE_NAME="atelierfit-crawl4ai"

if [ -z "${CRAWL4AI_API_TOKEN:-}" ]; then
  echo "Error: Please set CRAWL4AI_API_TOKEN before deploying."
  exit 1
fi

gcloud builds submit ./deploy/crawl4ai \
  --tag "gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

gcloud run deploy "${SERVICE_NAME}" \
  --image "gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest" \
  --region "${REGION}" \
  --platform managed \
  --port 11235 \
  --memory 2Gi \
  --cpu 2 \
  --concurrency 4 \
  --timeout 60s \
  --set-env-vars "CRAWL4AI_API_TOKEN=${CRAWL4AI_API_TOKEN}" \
  --allow-unauthenticated

echo "Crawl4AI Cloud Run deployment complete."
echo "Set CRAWL4AI_BASE_URL to the deployed Cloud Run URL in AI Studio Secrets."
