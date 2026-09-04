#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-philchen-project-elevate}"
REGION="${GOOGLE_CLOUD_REGION:-asia-southeast1}"
SERVICE_NAME="altostrat-hr-agent"

echo "================================================================="
echo " Deploying Altostrat HR Agent to Cloud Run"
echo " Project : ${PROJECT_ID}"
echo " Region  : ${REGION}"
echo " Service : ${SERVICE_NAME}"
echo " Source  : ${SCRIPT_DIR}"
echo "================================================================="

gcloud config set project "${PROJECT_ID}"

# Enable required Google Cloud APIs
echo "Enabling necessary Google Cloud services..."
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    aiplatform.googleapis.com \
    cloudbuild.googleapis.com \
    --project "${PROJECT_ID}"

# Deploy directly via Cloud Run source build
echo "Deploying Cloud Run service..."
gcloud run deploy "${SERVICE_NAME}" \
    --source . \
    --project "${PROJECT_ID}" \
    --region "${REGION}" \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=global,GOOGLE_GENAI_USE_VERTEXAI=true,GEMINI_MODEL=gemini-3.5-flash,SIMULATE_MCP=true" \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 5

echo "================================================================="
echo "Deployment complete! Service URL:"
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --platform managed \
    --region "${REGION}" \
    --project "${PROJECT_ID}" \
    --format="value(status.url)")

echo "Gemini App URL: ${SERVICE_URL}"
echo "Health Check : ${SERVICE_URL}/healthz"
echo "================================================================="
