"""Shared pytest fixtures. Forces local mode and stubs cloud clients."""
import io
import os

import pytest
from PIL import Image

os.environ["ENVIRONMENT"] = "local"
os.environ["LOCAL_API_KEY"] = "dev-key-12345"


def make_image_bytes(fmt: str = "JPEG", size: tuple[int, int] = (64, 64)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color=(120, 80, 40)).save(buf, format=fmt)
    return buf.getvalue()


@pytest.fixture
def jpeg_bytes() -> bytes:
    return make_image_bytes("JPEG")


@pytest.fixture
def png_bytes() -> bytes:
    return make_image_bytes("PNG")
