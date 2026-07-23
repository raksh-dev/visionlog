"""Image preprocessing for MobileNetV2.

Note: we deliberately avoid importing TensorFlow here. The MobileNetV2
preprocessing step (scaling pixels to [-1, 1]) is a trivial arithmetic
operation, so we implement it with numpy alone. This keeps the worker's
memory footprint and cold-start time low — the heavy model lives in Vertex AI.
"""
import io

import numpy as np
from PIL import Image

TARGET_SIZE = (224, 224)


def preprocess_image(image_bytes: bytes) -> np.ndarray:
    """Decode -> RGB -> resize 224x224 -> float32 -> scale to [-1, 1].

    Returns an array of shape (224, 224, 3). The Vertex endpoint treats the
    `instances` list as the batch dimension, so a single instance is one image.
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        img = img.convert("RGB")  # collapses RGBA / grayscale / palette to 3 channels
        img = img.resize(TARGET_SIZE, Image.LANCZOS)
        arr = np.asarray(img, dtype=np.float32)

    # Equivalent to tf.keras.applications.mobilenet_v2.preprocess_input:
    #   scaled = (pixel / 127.5) - 1.0  -> range [-1, 1]
    arr = (arr / 127.5) - 1.0
    return arr  # shape (224, 224, 3)


def to_instance(arr: np.ndarray) -> dict:
    """Convert the array into the Vertex AI instance payload."""
    return {"inputs": arr.tolist()}
