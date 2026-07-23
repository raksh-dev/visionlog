"""Smoke-test the deployed Vertex AI endpoint with a synthetic image.

Usage:
    python infra/scripts/setup_vertex_model.py --project-id P --region us-central1 --endpoint-id 123
"""
import argparse

import numpy as np
from google.cloud import aiplatform


def main(project_id: str, region: str, endpoint_id: str) -> None:
    aiplatform.init(project=project_id, location=region)
    endpoint = aiplatform.Endpoint(
        endpoint_name=f"projects/{project_id}/locations/{region}/endpoints/{endpoint_id}"
    )
    # A random [-1, 1] image just to confirm the endpoint responds.
    instance = {"inputs": ((np.random.rand(224, 224, 3).astype("float32")) * 2 - 1).tolist()}
    resp = endpoint.predict(instances=[instance])
    probs = resp.predictions[0]
    top = int(np.argmax(probs))
    print(f"Endpoint OK. Output length={len(probs)} top_index={top} conf={probs[top]:.4f}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--project-id", required=True)
    p.add_argument("--region", default="us-central1")
    p.add_argument("--endpoint-id", required=True)
    args = p.parse_args()
    main(args.project_id, args.region, args.endpoint_id)
