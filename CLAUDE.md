# CLAUDE.md — AI Agent Operating Manual for VisionLog

This file gives an AI coding agent the context of having already studied this
codebase. Read [GAPS.md](GAPS.md) before making improvements and
[PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) for the full architecture narrative.

## 1. Project identity

- **What:** VisionLog — an event-driven image classification platform on GCP.
  Users upload an image; MobileNetV2 on Vertex AI classifies it; the React UI
  shows top-3 ImageNet predictions.
- **Users:** demo/end users via the React app; potentially API consumers via
  the gateway. Single shared API key — there is **no per-user identity**.
- **Current state:** feature-complete skeleton with strong local dev story.
  Several P0 correctness bugs on the *cloud* path are documented in GAPS.md
  (§11) — the current development goal is fixing those before adding features.

## 2. Architecture in one paragraph

React (Vite) → API Gateway → **upload-service** (FastAPI, Cloud Run, always-on)
validates the file, writes the image to GCS `uploads/{requestId}/original.{ext}`
plus a `metadata.json` sidecar, and creates a `PENDING` doc (id = requestId,
UUID4) in the Firestore `predictions` collection. The GCS finalize event →
Eventarc → **inference-worker** (Cloud Run Function gen2, entry point
`handle_event`) downloads the image, preprocesses in numpy (224×224, [-1,1],
NO TensorFlow), calls the Vertex AI endpoint (`{"inputs": nested_list}` per
instance; `predictions[0]` = 1000-float softmax vector), decodes top-3 labels
from `src/labels/imagenet_labels.json`, and updates the doc to `COMPLETED`
(or `FAILED` — it always writes a terminal state and re-raises). The frontend
polls `GET /v1/images/{id}/status` every 2 s. Status machine:
`PENDING → PROCESSING → COMPLETED | FAILED`.

Key files: `services/upload-service/src/main.py` (all endpoints + response
models), `services/inference-worker/src/main.py` (the whole worker flow),
`infra/scripts/deploy.sh` (how everything lands in GCP).

`ENVIRONMENT=local` mode: filesystem storage (`local-uploads/`), Firestore
emulator, hardcoded key `dev-key-12345`, **no inference** — local records stay
`PENDING` forever by design; don't "fix" that.

## 3. Coding standards (observed conventions — match them)

- **Python 3.11**, flake8, max line length 100, `extend-ignore = E203,W503`.
  Type hints in modern syntax (`str | None`). Google-style module docstrings
  explaining *why*, short inline comments only for non-obvious constraints.
- **Field naming:** Python code is snake_case; **all JSON/API/Firestore fields
  are camelCase** (`requestId`, `uploadedAt`, `processingDurationMs`). Keep it.
- **Lazy imports** of `google.cloud.*` inside methods — deliberate, so local
  mode and tests never import cloud SDKs. Preserve this pattern.
- **Singletons:** clients and settings are module-level cached
  (`get_settings()`, `get_storage_client()`, …). Tests reset via
  `get_settings.cache_clear()` and `reset_api_key_cache()`. If you add a cached
  client, add a reset hook.
- **Errors:** validators raise `ValidationError(message, http_status)`; handlers
  translate to `JSONResponse({"detail": ...})`. Unexpected persistence errors →
  logged with `severity="ERROR"` + generic 500 detail. Never leak internals in
  responses (the worker currently violates this — GAPS G-S5).
- **Logging:** always via `log_event(logger, msg, severity=..., **fields)` —
  one JSON object per line for Cloud Logging. Include `requestId` on every
  pipeline event so a request is traceable end-to-end.
- **Frontend:** React 18 function components + hooks, Tailwind utility classes
  inline, no state library (useState/useEffect only), thin fetch wrapper in
  `src/api/visionlog.js`. No TypeScript — plain JSX.
- **Tests:** pytest with monkeypatched fakes; upload service enforces
  **80% coverage** via `pytest.ini` (`--cov-fail-under=80`) — new code without
  tests will fail CI.

## 4. Commands

```bash
# Local stack (API :8080, frontend :5173, emulator :8081)
docker compose up --build

# Upload service tests (coverage-gated)
cd services/upload-service && pip install -r requirements.txt && pytest

# Inference worker tests
cd services/inference-worker && pip install -r requirements.txt && pytest

# Lint (same as CI)
flake8 services --max-line-length=100 --extend-ignore=E203,W503
cd frontend && npm install && npm run lint

# Frontend dev/build
cd frontend && npm run dev    # or: npm run build

# Cloud deploy (see README §Deploy; note GAPS G-D1 — step 1 fails as written)
cd infra/scripts && ./deploy.sh PROJECT_ID us-central1
```

There are no DB migrations (Firestore is schemaless; composite indexes live in
`infra/terraform/firestore.tf`).

## 5. Environment variables

See the table in PROJECT_OVERVIEW.md §6. The ones that change behavior:

- `ENVIRONMENT` — `local` skips Secret Manager/GCS and uses `LOCAL_API_KEY`;
  `production` disables `/docs` and `/redoc`.
- `CORS_ORIGINS` — defaults to `*`; must be set explicitly in production.
- `VERTEX_ENDPOINT_ID` (worker) — numeric ID or full resource name; empty value
  silently produces a broken endpoint name.
- `VITE_API_BASE_URL` / `VITE_API_KEY` — baked into the frontend bundle at
  build time (which is itself a known security gap, G-S1).

Never commit real secrets. `.env` is gitignored; the committed `.env.example`
holds only dev placeholders. The production API key lives in Secret Manager
(`visionlog-api-key`); the dev key `dev-key-12345` is intentionally public.

## 6. Known constraints & fragile areas (do not break)

1. **Firestore record contract is triplicated** — the record dict in upload
   `main.py`, the update payloads in worker `firestore_client.py`, and the
   Pydantic response models must agree on names *and types*. There is a live
   type bug here (`processedAt`, GAPS G-B2). Any field change touches all three.
2. **GCS object naming** `uploads/{requestId}/original.{ext}` — the worker's
   `_extract_request_id` parses it and the Eventarc filter assumes the bucket.
   The `metadata.json` sidecar is deliberately skipped by the worker.
3. **Vertex payload contract** — `to_instance` produces
   `{"inputs": (224,224,3) list}`; the `instances` array is the batch dim.
   Payload size is near/over the 1.5 MB Vertex limit (GAPS G-B4) — don't add
   precision or extra fields.
4. **Write order in `upload_image`** (image → metadata → Firestore) races the
   GCS event (GAPS G-B1). The correct fix is Firestore-record-first; don't
   reorder casually in either direction without addressing the race.
5. **Worker label file** must be the real 1000-entry ImageNet list in
   `services/inference-worker/src/labels/`; the committed one is a placeholder
   (GAPS G-B3). Label index i must match the served model's class i.
6. **Middleware order** in upload `main.py`: CORS is added *after* auth so it
   runs first and handles OPTIONS preflight without a key. Keep that order.
7. **API key caching** — fetched once per instance; rotation requires restart.
8. **Two deploy paths** (`deploy.sh` and `.github/workflows/deploy.yml`) that
   already disagree on env vars (GAPS G-D3). If you change one, change both.
9. **80% coverage gate** on upload-service — significant untested additions
   will fail CI even if correct.
10. **This working copy is not a git repo** (GAPS G-D4) — no commits/branches
    are possible until `git init` is run; be careful with destructive edits.

## 7. Development rules for AI agents

- Inspect all three copies of the record contract (rule 6.1) before touching
  any Firestore field; grep for the camelCase field name across `services/`
  and `frontend/`.
- Preserve the existing architecture (async event-driven pipeline, lazy cloud
  imports, local-mode fallback) unless the user explicitly asks to change it.
- Add or update tests when changing behavior; follow the existing monkeypatch
  style in `services/*/tests/`. Prefer adding the missing emulator-backed
  integration test (GAPS G-T1) when touching the record lifecycle.
- Do not rewrite modules wholesale; the code style is consistent — make
  surgical edits that match it.
- Do not hardcode secrets, project IDs, or endpoint IDs; everything goes
  through `config.py` env vars with sensible local defaults.
- Do not remove functionality (e.g. local mode, metadata sidecar, structured
  logging fields) without calling it out explicitly.
- Keep README/PROJECT_OVERVIEW/GAPS in sync with behavior changes; when you
  fix a GAPS item, update its entry (and the summary in §9 below).

## 8. Project-specific how-tos

- **New API endpoint:** add the route + Pydantic response model in upload
  `src/main.py`; decide auth exposure (`PUBLIC_PATHS` in
  `middleware/api_key_auth.py` is the exemption list); mirror the route in
  `services/upload-service/openapi.yaml` so API Gateway proxies it; add tests
  in `tests/test_main.py` using the fake-client fixture.
- **New validation rule:** `src/validators.py` + tests in
  `tests/test_validators.py`; map to a specific HTTP status via
  `ValidationError(msg, status)`.
- **Frontend change:** components under `frontend/src/components/`; API calls
  only through `src/api/visionlog.js`; routes registered in `src/main.jsx`.
  Status badge colors are duplicated in `Dashboard.jsx` and `StatusPoller.jsx`
  (`BADGE` maps) — update both or extract.
- **Worker/inference change:** keep preprocessing numpy-only (no TF import);
  any change to the instance shape must be validated against the deployed
  SavedModel signature (`infra/scripts/setup_vertex_model.py` smoke-tests it).
- **New model version:** re-run `model/export_model.py` +
  `model/upload_to_vertex.py`, store the new endpoint ID in the
  `visionlog-vertex-endpoint-id` secret, bump `MODEL_VERSION`, and ensure the
  worker's labels file matches the new model's class indices.
- **Infra change:** Terraform in `infra/terraform/` owns APIs/IAM/GCS/
  Firestore/secrets/gateway; the worker function and Vertex model are deployed
  imperatively (`deploy.sh`, `model/*.py`). Beware the bootstrap-order and
  duplicate-trigger issues (GAPS G-D1, G-D2) before "fixing" either side.

## 9. Known gaps summary (check GAPS.md before starting work)

P0 (broken cloud paths): status endpoint 500s on completed records
(`processedAt` type mismatch, G-B2); worker ships placeholder labels →
mislabeled predictions (G-B3); GCS-event/Firestore-record race with retries
disabled → stuck PENDING (G-B1); CI deploys the worker without
`VERTEX_ENDPOINT_ID` (G-D3); first `terraform apply` fails (G-D1).

P1 highlights: API key is public in the JS bundle + wildcard CORS + no tenancy
(G-S1..3); duplicate Eventarc triggers (G-D2); no integration/E2E tests (G-T1);
Vertex payload size unverified (G-B4); infinite frontend polling (G-F1).

## 10. Safe next steps (suggested order)

1. `git init` + initial commit (G-D4) so subsequent fixes are reviewable.
2. Fix G-B2 (write `processedAt` as ISO string in the worker — smallest diff),
   with an integration-style test that feeds worker-written types through
   `StatusResponse`.
3. Fix G-B3 (commit the real 1000-label file to the worker).
4. Fix G-B1 (create Firestore record before the GCS write; `--retry` on
   function deploy; upsert in `mark_failed`).
5. Align `deploy.yml` env vars with `deploy.sh` (G-D3) and de-duplicate the
   Eventarc trigger (G-D2).
6. Add the emulator-backed integration test suite (G-T1) as the regression net.
7. Then frontend polish (G-F1 polling timeout) and the P2 list in GAPS §11.

**Needs human confirmation first:** the auth model decision (G-S1 — public
demo vs. real user auth changes the architecture), any Terraform restructure
(G-D1 — touches live state ordering), deleting/regenerating the Vertex
endpoint (cost + downtime), and enabling Firestore TTL (data deletion).
