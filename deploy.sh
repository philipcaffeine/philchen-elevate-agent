#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="philchen-project-elevate"
REGION="asia-southeast1"
SERVICE_NAME="altostrat-hr-agent"

echo "================================================================="
echo " Deploying Altostrat HR Agent to Cloud Run"
echo " Project : ${PROJECT_ID}"
echo " Region  : ${REGION}"
echo " Service : ${SERVICE_NAME}"
echo "================================================================="

gcloud config set project "${PROJECT_ID}"

# Enable required Google Cloud APIs
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    aiplatform.googleapis.com \
    cloudbuild.googleapis.com \
    --project "${PROJECT_ID}"

# Deploy directly via Cloud Run source build
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

echo "Deployment complete! Service URL:"
gcloud run services describe "${SERVICE_NAME}" \
    --platform managed \
    --region "${REGION}" \
    --project "${PROJECT_ID}" \
    --format="value(status.url)"
