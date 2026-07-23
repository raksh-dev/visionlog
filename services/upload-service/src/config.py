"""Central configuration loaded from environment variables.

All settings have sensible defaults for local development. In production
these are injected by Cloud Run / Secret Manager.
"""
from functools import lru_cache
import os


class Settings:
    def __init__(self) -> None:
        # "local" | "staging" | "production"
        self.environment: str = os.getenv("ENVIRONMENT", "local").lower()

        self.gcp_project_id: str = os.getenv("GCP_PROJECT_ID", "visionlog-local")
        self.gcp_region: str = os.getenv("GCP_REGION", "us-central1")

        self.gcs_bucket_name: str = os.getenv(
            "GCS_BUCKET_NAME", f"visionlog-images-{self.gcp_project_id}"
        )
        self.firestore_collection: str = os.getenv("FIRESTORE_COLLECTION", "predictions")

        # Secret Manager resource name that holds the API key.
        self.api_key_secret_name: str = os.getenv("API_KEY_SECRET_NAME", "visionlog-api-key")

        # Used only when ENVIRONMENT == "local" so we never touch Secret Manager.
        self.local_api_key: str = os.getenv("LOCAL_API_KEY", "dev-key-12345")

        # Firestore emulator host (set automatically by docker-compose locally).
        self.firestore_emulator_host: str | None = os.getenv("FIRESTORE_EMULATOR_HOST")

        # Where to dump images when running locally (no GCS).
        self.local_upload_dir: str = os.getenv("LOCAL_UPLOAD_DIR", "/tmp/uploads")

        self.log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
        self.service_version: str = os.getenv("SERVICE_VERSION", "1.0.0")

        # Comma-separated list of allowed CORS origins in production.
        self.cors_origins: list[str] = [
            o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()
        ]

        # Validation limits
        self.max_file_size_bytes: int = int(os.getenv("MAX_FILE_SIZE_BYTES", str(10 * 1024 * 1024)))
        self.min_dimension_px: int = int(os.getenv("MIN_DIMENSION_PX", "32"))

    @property
    def is_local(self) -> bool:
        return self.environment == "local"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
