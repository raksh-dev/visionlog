"""Firestore updates for the inference worker."""
from .config import get_settings


class FirestoreClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None

    def _doc(self, request_id: str):
        if self._client is None:
            from google.cloud import firestore

            self._client = firestore.Client(project=self.settings.gcp_project_id)
        return self._client.collection(self.settings.firestore_collection).document(request_id)

    def mark_processing(self, request_id: str) -> None:
        self._doc(request_id).update({"status": "PROCESSING"})

    def mark_completed(
        self, request_id: str, predictions: list[dict], duration_ms: int, endpoint_id: str
    ) -> None:
        from google.cloud import firestore

        self._doc(request_id).update(
            {
                "status": "COMPLETED",
                "processedAt": firestore.SERVER_TIMESTAMP,
                "predictions": predictions,
                "modelId": endpoint_id,
                "modelVersion": self.settings.model_version,
                "processingDurationMs": duration_ms,
                "errorMessage": None,
            }
        )

    def mark_failed(self, request_id: str, error_message: str) -> None:
        from google.cloud import firestore

        self._doc(request_id).update(
            {
                "status": "FAILED",
                "processedAt": firestore.SERVER_TIMESTAMP,
                "errorMessage": error_message,
            }
        )


_firestore_client: FirestoreClient | None = None


def get_firestore_client() -> FirestoreClient:
    global _firestore_client
    if _firestore_client is None:
        _firestore_client = FirestoreClient()
    return _firestore_client
