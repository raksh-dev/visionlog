#!/usr/bin/env bash
# End-to-end deploy helper. Requires: gcloud, terraform, docker, authenticated user.
set -euo pipefail

PROJECT_ID="${1:?Usage: deploy.sh PROJECT_ID [REGION]}"
REGION="${2:-us-central1}"
REPO="visionlog"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}"

echo ">> Setting project"
gcloud config set project "$PROJECT_ID"

echo ">> Ensuring Artifact Registry repo exists"
gcloud artifacts repositories create "$REPO" \
  --repository-format=docker --location="$REGION" 2>/dev/null || true
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

echo ">> Building & pushing upload-service image"
docker build -t "${REGISTRY}/upload-service:latest" ../../services/upload-service
docker push "${REGISTRY}/upload-service:latest"

echo ">> Applying Terraform infra"
pushd ../terraform >/dev/null
terraform init
terraform apply -auto-approve \
  -var="project_id=${PROJECT_ID}" \
  -var="region=${REGION}" \
  -var="upload_image=${REGISTRY}/upload-service:latest"
popd >/dev/null

echo ">> Deploying inference worker (Cloud Run Function, 2nd gen)"
gcloud functions deploy inference-worker \
  --gen2 --runtime=python311 --region="$REGION" \
  --source=../../services/inference-worker \
  --entry-point=handle_event \
  --trigger-event-filters="type=google.cloud.storage.object.v1.finalized" \
  --trigger-event-filters="bucket=visionlog-images-${PROJECT_ID}" \
  --memory=1Gi --cpu=1 --timeout=120s --max-instances=5 \
  --service-account="visionlog-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION},FIRESTORE_COLLECTION=predictions,VERTEX_ENDPOINT_ID=$(gcloud secrets versions access latest --secret=visionlog-vertex-endpoint-id)"

echo ">> Done."
