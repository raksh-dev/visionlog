"""VisionLog Upload Service.

A FastAPI application deployed to Cloud Run. It validates uploaded images,
stores them to GCS, writes a PENDING record to Firestore, and returns a
requestId immediately. It does NOT run inference — that happens asynchronously
in the inference worker, triggered by the GCS finalize event.
"""
import time
import uuid

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .config import get_settings
from .firestore_client import get_firestore_client, now_iso
from .logging_config import configure_logging, get_logger, log_event
from .middleware.api_key_auth import ApiKeyAuthMiddleware
from .storage import get_storage_client
from .validators import ValidationError, validate_upload

configure_logging()
logger = get_logger()
settings = get_settings()


# --------------------------------------------------------------------------- #
# Pydantic response models (drive the auto-generated OpenAPI docs)
# --------------------------------------------------------------------------- #
class Prediction(BaseModel):
    rank: int = Field(..., example=1)
    label: str = Field(..., example="golden retriever")
    confidence: float = Field(..., example=0.923)


class UploadResponse(BaseModel):
    requestId: str = Field(..., example="550e8400-e29b-41d4-a716-446655440000")
    status: str = Field(..., example="PENDING")
    message: str
    statusUrl: str


class StatusResponse(BaseModel):
    requestId: str
    status: str
    uploadedAt: str | None = None
    processedAt: str | None = None
    processingDurationMs: int | None = None
    fileName: str | None = None
    predictions: list[Prediction] = []
    modelVersion: str | None = None
    errorMessage: str | None = None


class ListItem(BaseModel):
    requestId: str
    fileName: str | None = None
    status: str
    uploadedAt: str | None = None
    predictions: list[Prediction] = []


class ListResponse(BaseModel):
    items: list[ListItem]
    nextCursor: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str


class ErrorResponse(BaseModel):
    detail: str


# --------------------------------------------------------------------------- #
# App setup
# --------------------------------------------------------------------------- #
# Disable interactive docs in production per the spec.
docs_url = None if settings.is_production else "/docs"
redoc_url = None if settings.is_production else "/redoc"

app = FastAPI(
    title="VisionLog Upload Service",
    version=settings.service_version,
    description="Asynchronous image-recognition upload API for the VisionLog platform.",
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_tags=[
        {"name": "images", "description": "Upload images and poll classification results."},
        {"name": "health", "description": "Service health checks."},
    ],
)

app.add_middleware(ApiKeyAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["X-API-Key", "Content-Type"],
)


def _to_predictions(raw: list[dict] | None) -> list[Prediction]:
    return [Prediction(**p) for p in (raw or [])]


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.post(
    "/v1/images/upload",
    tags=["images"],
    status_code=202,
    summary="Upload an image for classification",
    response_model=UploadResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or corrupt file"},
        401: {"model": ErrorResponse, "description": "Missing or invalid API key"},
        413: {"model": ErrorResponse, "description": "File too large"},
        415: {"model": ErrorResponse, "description": "Unsupported media type"},
        500: {"model": ErrorResponse, "description": "Storage or Firestore failure"},
    },
)
async def upload_image(request: Request, file: UploadFile = File(...)):
    """Accept a multipart image upload and queue it for asynchronous inference."""
    start = time.monotonic()
    content = await file.read()
    client_ip = request.client.host if request.client else None

    log_event(
        logger,
        "Image upload received",
        fileName=file.filename,
        mimeType=file.content_type,
        fileSizeBytes=len(content),
        clientIp=client_ip,
    )

    try:
        validated = validate_upload(file.filename, file.content_type, content)
    except ValidationError as exc:
        log_event(
            logger,
            "Image validation failed",
            severity="WARNING",
            reason=exc.message,
            fileName=file.filename,
        )
        return JSONResponse(status_code=exc.http_status, content={"detail": exc.message})

    request_id = str(uuid.uuid4())
    storage = get_storage_client()
    firestore = get_firestore_client()

    try:
        gcs_path = storage.store_image(
            request_id, validated.extension, validated.content, validated.mime_type
        )
        storage.store_metadata(
            request_id,
            {
                "requestId": request_id,
                "originalFileName": file.filename,
                "clientIp": client_ip,
                "uploadedAt": now_iso(),
            },
        )

        record = {
            "requestId": request_id,
            "fileName": f"{request_id}.{validated.extension}",
            "originalFileName": file.filename,
            "gcsPath": gcs_path,
            "gcsBucket": settings.gcs_bucket_name,
            "status": "PENDING",
            "uploadedAt": now_iso(),
            "processedAt": None,
            "fileSizeBytes": validated.size_bytes,
            "mimeType": validated.mime_type,
            "predictions": [],
            "modelId": None,
            "modelVersion": None,
            "errorMessage": None,
            "clientIp": client_ip,
            "processingDurationMs": None,
        }
        firestore.create_pending(record)
    except Exception as exc:  # noqa: BLE001
        log_event(
            logger,
            "Upload failed during persistence",
            severity="ERROR",
            requestId=request_id,
            error=str(exc),
        )
        return JSONResponse(
            status_code=500, content={"detail": "Failed to store image. Please retry."}
        )

    duration_ms = int((time.monotonic() - start) * 1000)
    log_event(
        logger,
        "Upload request completed",
        requestId=request_id,
        durationMs=duration_ms,
    )

    return UploadResponse(
        requestId=request_id,
        status="PENDING",
        message="Image uploaded successfully. Use the requestId to poll for results.",
        statusUrl=f"/v1/images/{request_id}/status",
    )


@app.get(
    "/v1/images/{request_id}/status",
    tags=["images"],
    summary="Get classification status and results",
    response_model=StatusResponse,
    responses={404: {"model": ErrorResponse, "description": "Unknown requestId"}},
)
async def get_status(request_id: str):
    """Return the current status, and predictions once classification completes."""
    record = get_firestore_client().get(request_id)
    if record is None:
        return JSONResponse(status_code=404, content={"detail": "requestId not found."})

    return StatusResponse(
        requestId=record["requestId"],
        status=record["status"],
        uploadedAt=record.get("uploadedAt"),
        processedAt=record.get("processedAt"),
        processingDurationMs=record.get("processingDurationMs"),
        fileName=record.get("originalFileName") or record.get("fileName"),
        predictions=_to_predictions(record.get("predictions")),
        modelVersion=record.get("modelVersion"),
        errorMessage=record.get("errorMessage"),
    )


@app.get(
    "/v1/images",
    tags=["images"],
    summary="List recent predictions (dashboard)",
    response_model=ListResponse,
)
async def list_images(limit: int = 20, status: str | None = None, cursor: str | None = None):
    """Return a paginated list of recent predictions for the dashboard."""
    limit = max(1, min(limit, 100))
    records = get_firestore_client().list_recent(limit=limit, status=status, cursor=cursor)
    items = [
        ListItem(
            requestId=r["requestId"],
            fileName=r.get("originalFileName") or r.get("fileName"),
            status=r["status"],
            uploadedAt=r.get("uploadedAt"),
            predictions=_to_predictions(r.get("predictions")),
        )
        for r in records
    ]
    next_cursor = records[-1].get("uploadedAt") if len(records) == limit else None
    return ListResponse(items=items, nextCursor=next_cursor)


@app.get("/health", tags=["health"], summary="Health check", response_model=HealthResponse)
async def health():
    """Liveness/readiness probe. No API key required."""
    return HealthResponse(status="ok", version=settings.service_version)
