"""Model loading and inference, independent of FastAPI transport code."""
import json
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent
model: Any | None = None
metadata: dict[str, Any] | None = None


def load_model_and_metadata() -> bool:
    """Load an approved, trusted model artifact once per application process."""
    global model, metadata
    model = None
    metadata = None
    try:
        with (ROOT / "model_metadata.json").open(encoding="utf-8") as file:
            loaded_metadata = json.load(file)
        if len(loaded_metadata.get("features", [])) != 13:
            raise ValueError("Expected exactly 13 features in model metadata")
        loaded_model = joblib.load(ROOT / "model.pkl")
    except Exception as exc:
        logger.warning("Model initialization failed: %s", exc)
        return False
    metadata = loaded_metadata
    model = loaded_model
    return True


def make_prediction(house_features: dict[str, Any]) -> float:
    """Order validated features as trained and predict a single house price."""
    if model is None or metadata is None:
        raise ValueError("Model not loaded")
    values = [house_features[name] for name in metadata["features"]]
    features = np.asarray([values], dtype=float)
    return round(float(model.predict(features)[0]), 2)


def get_model_info() -> dict[str, Any]:
    if metadata is None:
        raise ValueError("Model metadata not loaded")
    return metadata


def check_health() -> dict[str, Any]:
    ready = model is not None and metadata is not None
    return {
        "status": "healthy" if ready else "unhealthy",
        "model_loaded": model is not None,
        "message": "Model and metadata loaded successfully" if ready else "Model or metadata unavailable",
    }
