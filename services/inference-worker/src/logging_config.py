"""Structured JSON logging for Cloud Logging (inference worker)."""
import json
import logging
import sys
from datetime import datetime, timezone

from .config import get_settings


class CloudLoggingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "service": "inference-worker",
            "version": get_settings().service_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        json_fields = getattr(record, "json_fields", None)
        if isinstance(json_fields, dict):
            entry.update(json_fields)
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CloudLoggingFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(get_settings().log_level)


def get_logger(name: str = "visionlog.inference") -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger, message, severity="INFO", **fields) -> None:
    level = getattr(logging, severity.upper(), logging.INFO)
    logger.log(level, message, extra={"json_fields": fields})
