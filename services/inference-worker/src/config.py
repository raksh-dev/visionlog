"""Inference worker configuration from environment variables."""
import os


class Settings:
    def __init__(self) -> None:
        self.environment = os.getenv("ENVIRONMENT", "production").lower()
        self.gcp_project_id = os.getenv("GCP_PROJECT_ID", "visionlog-prod")
        self.gcp_region = os.getenv("GCP_REGION", "us-central1")
        self.firestore_collection = os.getenv("FIRESTORE_COLLECTION", "predictions")
        # Full Vertex AI endpoint resource name OR just the numeric ID.
        self.vertex_endpoint_id = os.getenv("VERTEX_ENDPOINT_ID", "")
        self.model_version = os.getenv("MODEL_VERSION", "mobilenetv2-v1")
        self.labels_path = os.getenv("LABELS_PATH", "src/labels/imagenet_labels.json")
        self.service_version = os.getenv("SERVICE_VERSION", "1.0.0")
        self.log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    def endpoint_resource_name(self) -> str:
        eid = self.vertex_endpoint_id
        if eid.startswith("projects/"):
            return eid
        return (
            f"projects/{self.gcp_project_id}/locations/"
            f"{self.gcp_region}/endpoints/{eid}"
        )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
