"""Portfolio-readable adaptation of the user's submitted TripleTen Sprint 10 code.

The lesson's instructional comments are omitted; the user's functional flow is preserved.
"""
import json
from typing import Any, Dict

import joblib
import numpy as np

model = None
metadata = None


def load_model_and_metadata():
    global model, metadata
    try:
        model = joblib.load("model.pkl")
        with open("model_metadata.json", "r", encoding="utf-8") as f:
            metadata = json.load(f)
        print("Model and metadata loaded successfully!")
        return True
    except Exception as e:
        print(f"Error loading model or metadata: {e}")
        return False


def make_prediction(house_features: Dict[str, Any]) -> float:
    global model
    if model is None:
        raise ValueError("Model not loaded")
    feature_values = [
        house_features[feature] for feature in metadata["features"]
    ]
    X = np.array([feature_values])
    prediction = model.predict(X)[0]
    return round(float(prediction), 2)


def get_model_info() -> Dict[str, Any]:
    global metadata
    if metadata is None:
        raise ValueError("Model metadata not loaded")
    return metadata


def check_health() -> Dict[str, Any]:
    global model, metadata
    is_healthy = model is not None and metadata is not None
    health_status = {
        "status": "healthy" if is_healthy else "unhealthy",
        "model_loaded": model is not None,
        "message": (
            "Model and metadata loaded successfully"
            if is_healthy
            else "Model or metadata is not loaded"
        ),
    }
    return health_status
