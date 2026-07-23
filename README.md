# VisionLog

A cloud-native, event-driven image recognition platform on Google Cloud Platform.

Upload an image → it's stored in GCS and a `PENDING` record is written to
Firestore → a GCS finalize event triggers an inference worker → the worker calls
a MobileNetV2 model hosted on Vertex AI → the Firestore record is updated to
`COMPLETED` with the top-3 predictions → the React frontend polls and displays
the result.

```
React → API Gateway → Upload Service (Cloud Run) → GCS + Firestore
                                                      │ (finalize event)
                                                   Eventarc
                                                      ▼
                                        Inference Worker (Cloud Run Function)
                                                      │
                                            Vertex AI (MobileNetV2)
                                                      ▼
                                                  Firestore ← polled by React
```

---

## Project structure

```
visionlog/
├── services/
│   ├── upload-service/          # FastAPI on Cloud Run (always-on HTTP)
│   │   ├── src/
│   │   │   ├── main.py              # endpoints + Pydantic schemas + Swagger
│   │   │   ├── validators.py        # file type/size/integrity checks
│   │   │   ├── storage.py           # GCS write (local FS fallback)
│   │   │   ├── firestore_client.py  # predictions collection access
│   │   │   ├── config.py            # env-driven settings
│   │   │   ├── logging_config.py    # structured JSON logs
│   │   │   └── middleware/api_key_auth.py
│   │   ├── tests/                   # pytest (validators, storage, endpoints)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── pytest.ini
│   │   └── openapi.yaml             # API Gateway spec
│   └── inference-worker/        # Cloud Run Function (Eventarc-triggered)
│       ├── src/
│       │   ├── main.py              # CloudEvent handler
│       │   ├── preprocessing.py     # decode/resize/scale (numpy, no TF)
│       │   ├── vertex_client.py     # Vertex predict + label decode
│       │   ├── firestore_client.py
│       │   ├── config.py
│       │   ├── logging_config.py
│       │   └── labels/imagenet_labels.json
│       ├── tests/
│       ├── Dockerfile
│       └── requirements.txt
├── frontend/                    # React 18 + Vite + Tailwind
│   └── src/{components,hooks,api,App.jsx,main.jsx}
├── infra/
│   ├── terraform/               # APIs, SA/IAM, GCS, Firestore, Cloud Run,
│   │                            #   Eventarc, Vertex secrets, API Gateway
│   └── scripts/{deploy.sh,setup_vertex_model.py}
├── model/                       # export_model.py, upload_to_vertex.py, labels/
├── docker-compose.yml           # local dev (emulator + service + frontend)
├── .env.example
└── .github/workflows/{ci.yml,deploy.yml}
```

---

## Prerequisites

- **Local dev:** Docker + Docker Compose, Node 20, Python 3.11
- **Cloud deploy:** a GCP project with billing, `gcloud`, `terraform >= 1.5`,
  Docker, and an authenticated account (`gcloud auth login`,
  `gcloud auth application-default login`)

---

## Run it locally (no GCP account needed)

Local mode (`ENVIRONMENT=local`) skips Secret Manager (uses a dev key), writes
images to `./local-uploads/`, and talks to the Firestore emulator.

```bash
cp .env.example .env
docker compose up --build
```

- Upload API: http://localhost:8080  (Swagger UI at http://localhost:8080/docs)
- Frontend:   http://localhost:5173
- Dev API key: `dev-key-12345` (header `X-API-Key`)

Quick smoke test:

```bash
curl -X POST http://localhost:8080/v1/images/upload \
  -H "X-API-Key: dev-key-12345" \
  -F "file=@/path/to/photo.jpg"
# → { "requestId": "...", "status": "PENDING", ... }

curl http://localhost:8080/v1/images/<requestId>/status -H "X-API-Key: dev-key-12345"
```

> Locally there is no Eventarc/Vertex, so records stay `PENDING` (the upload +
> storage + status flow is fully exercised). Inference runs only in the cloud.

### Run the tests

```bash
# Upload service (enforces 80% coverage)
cd services/upload-service && pip install -r requirements.txt && pytest

# Inference worker
cd services/inference-worker && pip install -r requirements.txt && pytest
```

---

## Deploy to GCP — step by step

### 1. Project + APIs + IAM (Terraform)

```bash
cd infra/terraform
terraform init
terraform apply -var="project_id=YOUR_PROJECT" -var="region=us-central1"
```

This enables all required APIs and creates the `visionlog-sa` service account
(least-privilege roles), GCS buckets, Firestore database + indexes, and the
`visionlog-api-key` / `visionlog-vertex-endpoint-id` secrets.

Then set the API key value:

```bash
echo -n "YOUR_STRONG_API_KEY" | gcloud secrets versions add visionlog-api-key --data-file=-
```

### 2. Build and deploy the Vertex AI model

```bash
cd model
pip install tensorflow google-cloud-aiplatform
python export_model.py     --project-id YOUR_PROJECT      # export + upload SavedModel + labels
python upload_to_vertex.py --project-id YOUR_PROJECT      # upload to registry + deploy endpoint
# prints ENDPOINT_ID — store it:
echo -n "ENDPOINT_ID" | gcloud secrets versions add visionlog-vertex-endpoint-id --data-file=-
```

Sanity-check the endpoint:

```bash
python infra/scripts/setup_vertex_model.py --project-id YOUR_PROJECT --endpoint-id ENDPOINT_ID
```

### 3. Deploy services (one command)

```bash
cd infra/scripts
./deploy.sh YOUR_PROJECT us-central1
```

This builds/pushes the upload-service image to Artifact Registry, re-applies
Terraform with the image, and deploys the inference worker as a 2nd-gen Cloud
Run Function wired to the GCS finalize event via Eventarc.

### 4. Configure API Gateway

Render `services/upload-service/openapi.yaml`, replacing `BACKEND_URL` with the
Cloud Run upload-service URL (`terraform output upload_service_url`), then save
it as `infra/terraform/openapi_rendered.yaml` and `terraform apply` again. Grab
the gateway URL with `terraform output api_gateway_url`.

### 5. Deploy the frontend

```bash
cd frontend
echo "VITE_API_BASE_URL=https://YOUR_GATEWAY_URL" >  .env.production
echo "VITE_API_KEY=YOUR_API_KEY"                  >> .env.production
npm install && npm run build      # outputs dist/ — host on Firebase Hosting or Cloud Run
```

### 6. CI/CD (optional)

`.github/workflows/ci.yml` runs tests + lint + a Docker build on every PR.
`.github/workflows/deploy.yml` deploys on merge to `main` using **Workload
Identity Federation** (no JSON keys). Set repo secrets: `WIF_PROVIDER`,
`WIF_SERVICE_ACCOUNT`, `VITE_API_BASE_URL`, `VITE_API_KEY`, `FIREBASE_SA`.

---

## End-to-end flow (cloud)

1. `POST /v1/images/upload` → upload-service validates, stores to GCS, writes
   `PENDING`, returns `requestId`.
2. GCS finalize → Eventarc → inference worker.
3. Worker downloads the image, preprocesses, calls Vertex AI, writes top-3
   predictions and `COMPLETED` to Firestore.
4. Frontend polls `GET /v1/images/{requestId}/status` every 2s until terminal.

---

## Notes & decisions

- **No TensorFlow in the worker.** MobileNetV2 preprocessing is just
  `pixel/127.5 - 1`; doing it in numpy keeps the worker light. The model lives
  in Vertex AI with `min_replica_count=1` to avoid cold starts.
- **Vertex instance shape.** Each `instances` entry is one `(224,224,3)` image;
  the `instances` list itself is the batch dimension (this is the correct TF
  Serving contract, and is what `preprocessing.to_instance` produces).
- **Defense-in-depth auth.** API Gateway validates the key, and the upload
  service re-validates it in middleware (cached after the first Secret Manager
  fetch). `/health` and docs routes are exempt.
- **Labels file.** A structurally-correct 1000-entry placeholder ships in the
  repo so things run; `model/export_model.py` regenerates the *real* ImageNet
  labels from Keras so indices line up exactly with the served model.
- **Docs in prod.** `/docs` and `/redoc` are disabled when
  `ENVIRONMENT=production`.
