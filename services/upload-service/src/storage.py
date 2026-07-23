"""Image storage abstraction.

In GCP we write to a private GCS bucket. Locally (ENVIRONMENT=local) we write
to a directory on disk so development needs no cloud credentials.
"""
import json
import os
from pathlib import Path

from .config import get_settings
from .logging_config import get_logger, log_event

logger = get_logger()


class StorageClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._gcs_client = None  # lazily created; avoids importing GCS locally

    def _bucket(self):
        if self._gcs_client is None:
            from google.cloud import storage  # imported lazily

            self._gcs_client = storage.Client(project=self.settings.gcp_project_id)
        return self._gcs_client.bucket(self.settings.gcs_bucket_name)

    def object_path(self, request_id: str, extension: str) -> str:
        return f"uploads/{request_id}/original.{extension}"

    def metadata_path(self, request_id: str) -> str:
        return f"uploads/{request_id}/metadata.json"

    def store_image(
        self, request_id: str, extension: str, content: bytes, mime_type: str
    ) -> str:
        """Persist the image and return the storage path (relative key)."""
        path = self.object_path(request_id, extension)

        if self.settings.is_local:
            target = Path(self.settings.local_upload_dir) / request_id / f"original.{extension}"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            log_event(logger, "Image stored locally", path=str(target), requestId=request_id)
            return path

        blob = self._bucket().blob(path)
        blob.upload_from_string(content, content_type=mime_type)
        log_event(logger, "Image stored to GCS", path=path, requestId=request_id)
        return path

    def store_metadata(self, request_id: str, metadata: dict) -> None:
        path = self.metadata_path(request_id)
        payload = json.dumps(metadata, default=str)

        if self.settings.is_local:
            target = Path(self.settings.local_upload_dir) / request_id / "metadata.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(payload)
            return

        blob = self._bucket().blob(path)
        blob.upload_from_string(payload, content_type="application/json")


_storage_client: StorageClient | None = None


def get_storage_client() -> StorageClient:
    global _storage_client
    if _storage_client is None:
        _storage_client = StorageClient()
    return _storage_client
