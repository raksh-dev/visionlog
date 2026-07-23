"""File validation for uploaded images.

Validation runs *before* any GCS/Firestore write so we never persist garbage.
Each check maps to a specific HTTP error in main.py.
"""
import io
from dataclasses import dataclass

from PIL import Image

from .config import get_settings

# MIME type -> set of acceptable file extensions (lowercase, no dot)
ALLOWED_MIME_TYPES: dict[str, set[str]] = {
    "image/jpeg": {"jpg", "jpeg"},
    "image/png": {"png"},
    "image/webp": {"webp"},
}


class ValidationError(Exception):
    """Raised when an uploaded file fails validation.

    `http_status` lets main.py translate this into the correct response code.
    """

    def __init__(self, message: str, http_status: int = 400):
        super().__init__(message)
        self.message = message
        self.http_status = http_status


@dataclass
class ValidatedImage:
    content: bytes
    mime_type: str
    extension: str
    size_bytes: int
    width: int
    height: int


def _extension_from_filename(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()


def validate_upload(filename: str | None, mime_type: str | None, content: bytes) -> ValidatedImage:
    """Validate a single uploaded file. Raises ValidationError on failure."""
    settings = get_settings()

    if not content:
        raise ValidationError("Request must include a non-empty file field.", 400)

    size_bytes = len(content)
    if size_bytes > settings.max_file_size_bytes:
        raise ValidationError(
            f"File exceeds maximum size of {settings.max_file_size_bytes} bytes.", 413
        )

    if not mime_type or mime_type not in ALLOWED_MIME_TYPES:
        raise ValidationError(
            f"Unsupported media type '{mime_type}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_MIME_TYPES))}.",
            415,
        )

    extension = _extension_from_filename(filename or "")
    if extension not in ALLOWED_MIME_TYPES[mime_type]:
        raise ValidationError(
            f"File extension '.{extension}' does not match MIME type '{mime_type}'.", 400
        )

    # Integrity + dimension check via Pillow.
    try:
        with Image.open(io.BytesIO(content)) as img:
            img.verify()  # detects truncated/corrupt files
    except Exception as exc:  # noqa: BLE001 - Pillow raises many subclasses
        raise ValidationError(f"Image is corrupt or unreadable: {exc}", 400) from exc

    # verify() leaves the image unusable; reopen to read dimensions.
    with Image.open(io.BytesIO(content)) as img:
        width, height = img.size

    if width < settings.min_dimension_px or height < settings.min_dimension_px:
        raise ValidationError(
            f"Image dimensions {width}x{height} are below the minimum "
            f"{settings.min_dimension_px}x{settings.min_dimension_px}.",
            400,
        )

    return ValidatedImage(
        content=content,
        mime_type=mime_type,
        extension=extension,
        size_bytes=size_bytes,
        width=width,
        height=height,
    )
