import pytest

from src.validators import ValidationError, validate_upload
from tests.conftest import make_image_bytes


def test_valid_jpeg(jpeg_bytes):
    result = validate_upload("dog.jpg", "image/jpeg", jpeg_bytes)
    assert result.mime_type == "image/jpeg"
    assert result.extension == "jpg"
    assert result.width == 64


def test_valid_png(png_bytes):
    result = validate_upload("cat.png", "image/png", png_bytes)
    assert result.mime_type == "image/png"


def test_missing_file():
    with pytest.raises(ValidationError) as exc:
        validate_upload("x.jpg", "image/jpeg", b"")
    assert exc.value.http_status == 400


def test_unsupported_mime(jpeg_bytes):
    with pytest.raises(ValidationError) as exc:
        validate_upload("doc.pdf", "application/pdf", jpeg_bytes)
    assert exc.value.http_status == 415


def test_extension_mismatch(jpeg_bytes):
    with pytest.raises(ValidationError) as exc:
        validate_upload("dog.png", "image/jpeg", jpeg_bytes)
    assert exc.value.http_status == 400


def test_too_large(monkeypatch, jpeg_bytes):
    from src.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("MAX_FILE_SIZE_BYTES", "10")
    with pytest.raises(ValidationError) as exc:
        validate_upload("dog.jpg", "image/jpeg", jpeg_bytes)
    assert exc.value.http_status == 413
    get_settings.cache_clear()


def test_corrupt_image():
    with pytest.raises(ValidationError) as exc:
        validate_upload("dog.jpg", "image/jpeg", b"not-an-image" * 10)
    assert exc.value.http_status == 400


def test_too_small():
    tiny = make_image_bytes("JPEG", size=(16, 16))
    with pytest.raises(ValidationError) as exc:
        validate_upload("dog.jpg", "image/jpeg", tiny)
    assert exc.value.http_status == 400
