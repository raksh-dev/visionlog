import io
import os
from unittest.mock import MagicMock

import numpy as np
import pytest
from PIL import Image

os.environ["ENVIRONMENT"] = "test"
os.environ["LABELS_PATH"] = os.path.join(os.path.dirname(__file__), "fixtures_labels.json")

# Write a small label fixture (1000 entries) so vertex_client can decode.
_fixture = os.environ["LABELS_PATH"]
if not os.path.exists(_fixture):
    import json

    with open(_fixture, "w") as fh:
        json.dump([f"label_{i}" for i in range(1000)], fh)

from src.preprocessing import preprocess_image, to_instance  # noqa: E402
from src.vertex_client import top_k_predictions  # noqa: E402
import src.main as worker  # noqa: E402


def _img_bytes(fmt="JPEG", mode="RGB", size=(300, 200)):
    buf = io.BytesIO()
    Image.new(mode, size, color=(10, 120, 200)).save(buf, format=fmt)
    return buf.getvalue()


def test_preprocess_jpeg_shape():
    arr = preprocess_image(_img_bytes("JPEG"))
    assert arr.shape == (224, 224, 3)
    assert arr.dtype == np.float32
    assert arr.min() >= -1.0 and arr.max() <= 1.0


def test_preprocess_png_rgba():
    arr = preprocess_image(_img_bytes("PNG", mode="RGBA", size=(64, 64)))
    assert arr.shape == (224, 224, 3)  # RGBA collapsed to RGB


def test_to_instance():
    arr = preprocess_image(_img_bytes())
    inst = to_instance(arr)
    assert "inputs" in inst
    assert len(inst["inputs"]) == 224


def test_top3_extraction():
    probs = [0.0] * 1000
    probs[5] = 0.9
    probs[10] = 0.07
    probs[20] = 0.02
    top3 = top_k_predictions(probs, k=3)
    assert [p["rank"] for p in top3] == [1, 2, 3]
    assert top3[0]["label"] == "label_5"
    assert top3[0]["confidence"] == 0.9


def test_extract_request_id():
    assert worker._extract_request_id("uploads/abc-123/original.jpg") == "abc-123"
    assert worker._extract_request_id("random/file.txt") is None


class _FakeEvent:
    def __init__(self, data):
        self.data = data


def test_firestore_update_completed(monkeypatch):
    fs = MagicMock()
    monkeypatch.setattr(worker, "get_firestore_client", lambda: fs)
    monkeypatch.setattr(worker, "_download_image", lambda b, n: _img_bytes())

    vc = MagicMock()
    probs = [0.0] * 1000
    probs[1] = 0.95
    vc.predict.return_value = probs
    monkeypatch.setattr(worker, "get_vertex_client", lambda: vc)

    worker.handle_event(_FakeEvent({"bucket": "b", "name": "uploads/req-1/original.jpg"}))

    fs.mark_processing.assert_called_once_with("req-1")
    assert fs.mark_completed.called
    fs.mark_failed.assert_not_called()


def test_firestore_update_failed(monkeypatch):
    fs = MagicMock()
    monkeypatch.setattr(worker, "get_firestore_client", lambda: fs)

    def _boom(bucket, name):
        raise RuntimeError("download exploded")

    monkeypatch.setattr(worker, "_download_image", _boom)

    with pytest.raises(RuntimeError):
        worker.handle_event(_FakeEvent({"bucket": "b", "name": "uploads/req-2/original.jpg"}))

    fs.mark_failed.assert_called_once()
    assert "download exploded" in fs.mark_failed.call_args[0][1]


def test_metadata_object_ignored(monkeypatch):
    fs = MagicMock()
    monkeypatch.setattr(worker, "get_firestore_client", lambda: fs)
    worker.handle_event(_FakeEvent({"bucket": "b", "name": "uploads/req-3/metadata.json"}))
    fs.mark_processing.assert_not_called()
