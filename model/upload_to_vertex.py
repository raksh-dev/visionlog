"""Upload the SavedModel to Vertex AI Model Registry and deploy it to an endpoint.

Run locally after export_model.py:
    python model/upload_to_vertex.py --project-id YOUR_PROJECT --region us-central1

Prints the ENDPOINT_ID at the end — store it in Secret Manager as
visionlog-vertex-endpoint-id and set VERTEX_ENDPOINT_ID on the worker.
"""
import argparse

from google.cloud import aiplatform

SERVING_IMAGE = "us-docker.pkg.dev/vertex-ai/prediction/tf2-cpu.2-12:latest"


def main(project_id: str, region: str) -> None:
    aiplatform.init(project=project_id, location=region)

    model = aiplatform.Model.upload(
        display_name="visionlog-mobilenetv2",
        artifact_uri=f"gs://visionlog-models-{project_id}/mobilenetv2/v1/",
        serving_container_image_uri=SERVING_IMAGE,
        labels={"version": "v1", "framework": "tensorflow"},
    )
    print(f"Uploaded model: {model.resource_name}")

    endpoint = aiplatform.Endpoint.create(display_name="visionlog-endpoint")
    print(f"Created endpoint: {endpoint.resource_name}")

    model.deploy(
        endpoint=endpoint,
        machine_type="n1-standard-2",
        min_replica_count=1,  # keep warm — no endpoint cold starts
        max_replica_count=2,
        traffic_split={"0": 100},
    )

    endpoint_id = endpoint.resource_name.split("/")[-1]
    print("=" * 60)
    print(f"ENDPOINT_ID = {endpoint_id}")
    print("Store it: gcloud secrets create visionlog-vertex-endpoint-id "
          f'--data-file=<(echo -n "{endpoint_id}")')
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--region", default="us-central1")
    args = parser.parse_args()
    main(args.project_id, args.region)
