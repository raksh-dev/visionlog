"""VisionLog Inference Worker.

A 2nd-gen Cloud Run Function triggered by Eventarc on a GCS object-finalized
event. It downloads the uploaded image, preprocesses it, calls the Vertex AI
endpoint, decodes the top-3 ImageNet labels, and updates the Firestore record.

It always writes a terminal status (COMPLETED or FAILED) so no record is ever
left stuck in PENDING.
"""
import time

import functions_framework
from google.cloud import storage

from .config import get_settings
from .firestore_client import get_firestore_client
from .logging_config import configure_logging, get_logger, log_event
from .preprocessing import preprocess_image, to_instance
from .vertex_client import get_vertex_client, top_k_predictions

configure_logging()
logger = get_logger()


def _extract_request_id(object_name: str) -> str | None:
    """uploads/{requestId}/original.jpg -> {requestId}."""
    parts = object_name.split("/")
    if len(parts) >= 2 and parts[0] == "uploads":
        return parts[1]
    return None


def _download_image(bucket_name: str, object_name: str) -> bytes:
    client = storage.Client()
    blob = client.bucket(bucket_name).blob(object_name)
    return blob.download_as_bytes()


@functions_framework.cloud_event
def handle_event(cloud_event):
    """Entry point. Wired to the GCS finalize CloudEvent via Eventarc."""
    settings = get_settings()
    data = cloud_event.data
    bucket = data["bucket"]
    name = data["name"]

    request_id = _extract_request_id(name)
    if request_id is None:
        # Not an upload we care about (e.g. metadata.json or unexpected path).
        log_event(logger, "Ignoring non-upload object", severity="INFO", objectName=name)
        return

    # Skip the sidecar metadata file; we only classify the original image.
    if name.endswith("metadata.json"):
        return

    firestore = get_firestore_client()
    start = time.monotonic()
    log_event(logger, "Inference job started", requestId=request_id, gcsPath=name)

    try:
        firestore.mark_processing(request_id)

        image_bytes = _download_image(bucket, name)

        pre_start = time.monotonic()
        arr = preprocess_image(image_bytes)
        instance = to_instance(arr)
        log_event(
            logger,
            "Image preprocessed",
            requestId=request_id,
            durationMs=int((time.monotonic() - pre_start) * 1000),
        )

        probabilities = get_vertex_client().predict(instance)
        predictions = top_k_predictions(probabilities, k=3)

        top = predictions[0]
        log_event(
            logger,
            "Vertex AI prediction received",
            requestId=request_id,
            topPrediction=top["label"],
            confidence=top["confidence"],
        )

        duration_ms = int((time.monotonic() - start) * 1000)
        firestore.mark_completed(
            request_id, predictions, duration_ms, settings.vertex_endpoint_id
        )
        log_event(
            logger,
            "Firestore record updated to COMPLETED",
            requestId=request_id,
            durationMs=duration_ms,
            topPrediction=top["label"],
            confidence=top["confidence"],
            modelVersion=settings.model_version,
        )

    except Exception as exc:  # noqa: BLE001 - we must always record a terminal state
        log_event(
            logger,
            "Inference job failed",
            severity="ERROR",
            requestId=request_id,
            error=str(exc),
        )
        try:
            firestore.mark_failed(request_id, str(exc))
        except Exception as inner:  # noqa: BLE001
            log_event(
                logger,
                "Failed to write FAILED status to Firestore",
                severity="ERROR",
                requestId=request_id,
                error=str(inner),
            )
        # Re-raise so the platform records the failure / can retry.
        raise
