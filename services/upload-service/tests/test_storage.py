import os
from pathlib import Path

from src.storage import StorageClient


def test_object_path():
    client = StorageClient()
    assert client.object_path("abc", "jpg") == "uploads/abc/original.jpg"


def test_store_image_local(tmp_path, monkeypatch, jpeg_bytes):
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("LOCAL_UPLOAD_DIR", str(tmp_path))
    from src.config import get_settings

    get_settings.cache_clear()
    client = StorageClient()
    path = client.store_image("req-1", "jpg", jpeg_bytes, "image/jpeg")
    assert path == "uploads/req-1/original.jpg"
    assert (tmp_path / "req-1" / "original.jpg").read_bytes() == jpeg_bytes
    get_settings.cache_clear()


def test_store_metadata_local(tmp_path, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("LOCAL_UPLOAD_DIR", str(tmp_path))
    from src.config import get_settings

    get_settings.cache_clear()
    client = StorageClient()
    client.store_metadata("req-2", {"requestId": "req-2"})
    assert (tmp_path / "req-2" / "metadata.json").exists()
    get_settings.cache_clear()
