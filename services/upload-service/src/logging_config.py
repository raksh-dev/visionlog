"""Structured JSON logging compatible with Google Cloud Logging.

Cloud Logging interprets a JSON line on stdout and maps the `severity`
field and any extra keys into the structured log entry.
"""
import json
import logging
import sys
from datetime import datetime, timezone

from .config import get_settings


class CloudLoggingFormatter(logging.Formatter):
    """Emit one JSON object per log line."""

    def format(self, record: logging.LogRecord) -> str:
        settings = get_settings()
        entry = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "service": "upload-service",
            "version": settings.service_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        # Attach any structured context passed via `extra={"json_fields": {...}}`.
        json_fields = getattr(record, "json_fields", None)
        if isinstance(json_fields, dict):
            entry.update(json_fields)
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging() -> None:
    settings = get_settings()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CloudLoggingFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level)


def get_logger(name: str = "visionlog.upload") -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, message: str, severity: str = "INFO", **fields) -> None:
    """Helper to emit a structured event with arbitrary extra fields."""
    level = getattr(logging, severity.upper(), logging.INFO)
    logger.log(level, message, extra={"json_fields": fields})
