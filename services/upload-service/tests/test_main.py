from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import src.main as main
from src.main import app
from src.middleware.api_key_auth import reset_api_key_cache

API_KEY = "dev-key-12345"
HEADERS = {"X-API-Key": API_KEY}


@pytest.fixture(autouse=True)
def stub_clients(monkeypatch, tmp_path):
    """Replace storage + firestore with in-memory fakes."""
    reset_api_key_cache()

    fake_store = MagicMock()
    fake_store.store_image.return_value = "uploads/x/original.jpg"

    db: dict[str, dict] = {}

    fake_fs = MagicMock()
    fake_fs.create_pending.side_effect = lambda rec: db.__setitem__(rec["requestId"], rec)
    fake_fs.get.side_effect = lambda rid: db.get(rid)
    fake_fs.list_recent.side_effect = lambda **kw: list(db.values())[: kw.get("limit", 20)]

    monkeypatch.setattr(main, "get_storage_client", lambda: fake_store)
    monkeypatch.setattr(main, "get_firestore_client", lambda: fake_fs)
    return db


@pytest.fixture
def client():
    return TestClient(app)


def test_health_no_key(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_upload_missing_api_key(client, jpeg_bytes):
    resp = client.post(
        "/v1/images/upload", files={"file": ("dog.jpg", jpeg_bytes, "image/jpeg")}
    )
    assert resp.status_code == 401


def test_upload_wrong_api_key(client, jpeg_bytes):
    resp = client.post(
        "/v1/images/upload",
        headers={"X-API-Key": "nope"},
        files={"file": ("dog.jpg", jpeg_bytes, "image/jpeg")},
    )
    assert resp.status_code == 401


def test_upload_valid_jpeg(client, jpeg_bytes):
    resp = client.post(
        "/v1/images/upload",
        headers=HEADERS,
        files={"file": ("dog.jpg", jpeg_bytes, "image/jpeg")},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "PENDING"
    assert "requestId" in body


def test_upload_valid_png(client, png_bytes):
    resp = client.post(
        "/v1/images/upload",
        headers=HEADERS,
        files={"file": ("cat.png", png_bytes, "image/png")},
    )
    assert resp.status_code == 202


def test_upload_invalid_type(client, jpeg_bytes):
    resp = client.post(
        "/v1/images/upload",
        headers=HEADERS,
        files={"file": ("doc.pdf", jpeg_bytes, "application/pdf")},
    )
    assert resp.status_code == 415


def test_upload_corrupt_image(client):
    resp = client.post(
        "/v1/images/upload",
        headers=HEADERS,
        files={"file": ("dog.jpg", b"garbage" * 5, "image/jpeg")},
    )
    assert resp.status_code == 400


def test_status_pending(client, jpeg_bytes):
    up = client.post(
        "/v1/images/upload",
        headers=HEADERS,
        files={"file": ("dog.jpg", jpeg_bytes, "image/jpeg")},
    )
    rid = up.json()["requestId"]
    resp = client.get(f"/v1/images/{rid}/status", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json()["status"] == "PENDING"


def test_status_not_found(client):
    resp = client.get("/v1/images/does-not-exist/status", headers=HEADERS)
    assert resp.status_code == 404


def test_list_predictions(client, jpeg_bytes):
    client.post(
        "/v1/images/upload",
        headers=HEADERS,
        files={"file": ("dog.jpg", jpeg_bytes, "image/jpeg")},
    )
    resp = client.get("/v1/images?limit=10", headers=HEADERS)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) >= 1
