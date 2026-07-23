"""Firestore access for the predictions collection.

Works against the real Firestore in GCP and against the emulator locally
(the google-cloud-firestore client honours FIRESTORE_EMULATOR_HOST).
"""
from datetime import datetime, timezone

from .config import get_settings
from .logging_config import get_logger, log_event

logger = get_logger()


class FirestoreClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None

    def _db(self):
        if self._client is None:
            from google.cloud import firestore  # imported lazily

            self._client = firestore.Client(project=self.settings.gcp_project_id)
        return self._client

    def _collection(self):
        return self._db().collection(self.settings.firestore_collection)

    def create_pending(self, record: dict) -> None:
        request_id = record["requestId"]
        self._collection().document(request_id).set(record)
        log_event(logger, "Firestore PENDING record created", requestId=request_id)

    def get(self, request_id: str) -> dict | None:
        snap = self._collection().document(request_id).get()
        if not snap.exists:
            return None
        return snap.to_dict()

    def list_recent(
        self, limit: int = 20, status: str | None = None, cursor: str | None = None
    ) -> list[dict]:
        from google.cloud import firestore  # imported lazily

        query = self._collection()
        if status:
            query = query.where("status", "==", status)
        query = query.order_by("uploadedAt", direction=firestore.Query.DESCENDING)
        if cursor:
            query = query.start_after({"uploadedAt": cursor})
        query = query.limit(limit)
        return [doc.to_dict() for doc in query.stream()]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_firestore_client: FirestoreClient | None = None


def get_firestore_client() -> FirestoreClient:
    global _firestore_client
    if _firestore_client is None:
        _firestore_client = FirestoreClient()
    return _firestore_client
