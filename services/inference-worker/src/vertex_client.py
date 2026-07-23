"""Vertex AI prediction client + label decoding."""
import json
from pathlib import Path

from .config import get_settings

_labels_cache: list[str] | None = None


def load_labels() -> list[str]:
    """Load and cache the ImageNet label list (index -> human-readable label)."""
    global _labels_cache
    if _labels_cache is None:
        path = Path(get_settings().labels_path)
        with path.open() as fh:
            _labels_cache = json.load(fh)
    return _labels_cache


def top_k_predictions(probabilities: list[float], k: int = 3) -> list[dict]:
    """Return the top-k predictions as ranked label/confidence dicts."""
    labels = load_labels()
    top_idx = sorted(range(len(probabilities)), key=lambda i: probabilities[i], reverse=True)[:k]
    results = []
    for rank, idx in enumerate(top_idx):
        label = labels[idx] if idx < len(labels) else f"class_{idx}"
        results.append(
            {"rank": rank + 1, "label": label, "confidence": round(float(probabilities[idx]), 4)}
        )
    return results


class VertexClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._endpoint = None

    def _get_endpoint(self):
        if self._endpoint is None:
            from google.cloud import aiplatform

            aiplatform.init(
                project=self.settings.gcp_project_id, location=self.settings.gcp_region
            )
            self._endpoint = aiplatform.Endpoint(
                endpoint_name=self.settings.endpoint_resource_name()
            )
        return self._endpoint

    def predict(self, instance: dict) -> list[float]:
        """Call the Vertex AI endpoint and return the probability vector."""
        endpoint = self._get_endpoint()
        response = endpoint.predict(instances=[instance])
        # predictions[0] is the 1000-length probability/logit vector for our 1 image.
        return list(response.predictions[0])


_vertex_client: VertexClient | None = None


def get_vertex_client() -> VertexClient:
    global _vertex_client
    if _vertex_client is None:
        _vertex_client = VertexClient()
    return _vertex_client
