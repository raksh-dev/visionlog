"""Export MobileNetV2 (ImageNet) to TensorFlow SavedModel format and upload to GCS.

Run locally (needs tensorflow + gcloud auth):
    python model/export_model.py --project-id YOUR_PROJECT

It also regenerates labels/imagenet_labels.json from Keras so indices match
exactly what the served model produces.
"""
import argparse
import json
import os
import subprocess

import tensorflow as tf


def export_savedmodel(out_dir: str) -> None:
    model = tf.keras.applications.MobileNetV2(weights="imagenet")
    # The model already ends in a softmax over 1000 ImageNet classes.
    model.export(out_dir)  # TF 2.13+: writes a SavedModel directory
    print(f"SavedModel written to {out_dir}")


def export_labels(labels_path: str) -> None:
    """Write index -> label list using Keras' canonical class index."""
    # keras stores imagenet_class_index.json with {"0": ["n01440764", "tench"], ...}
    path = tf.keras.utils.get_file(
        "imagenet_class_index.json",
        "https://storage.googleapis.com/download.tensorflow.org/data/imagenet_class_index.json",
    )
    with open(path) as fh:
        idx = json.load(fh)
    labels = [idx[str(i)][1] for i in range(1000)]
    os.makedirs(os.path.dirname(labels_path), exist_ok=True)
    with open(labels_path, "w") as fh:
        json.dump(labels, fh, indent=0)
    print(f"Labels written to {labels_path}")


def upload_to_gcs(local_dir: str, gcs_uri: str) -> None:
    subprocess.run(["gsutil", "-m", "cp", "-r", f"{local_dir}/*", gcs_uri], check=True)
    print(f"Uploaded SavedModel to {gcs_uri}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--out-dir", default="./saved_model")
    parser.add_argument("--labels-path", default="./labels/imagenet_labels.json")
    args = parser.parse_args()

    export_savedmodel(args.out_dir)
    export_labels(args.labels_path)

    gcs_uri = f"gs://visionlog-models-{args.project_id}/mobilenetv2/v1/"
    upload_to_gcs(args.out_dir, gcs_uri)
    print("Done. Next: python model/upload_to_vertex.py --project-id", args.project_id)
