"""Offline interface tests; they deliberately do not use the course model file."""
import json
from pathlib import Path

from fastapi.testclient import TestClient
import numpy as np
import pytest

import api
from main import app
from schemas import HousePredictionRequest


class FakeEstimator:
    def __init__(self):
        self.last_shape = None
        self.last_values = None

    def predict(self, features):
        self.last_shape = features.shape
        self.last_values = features[0].tolist()
        return np.array([480032.65])


@pytest.fixture
def client():
    with TestClient(app) as http:
        data = json.loads((Path(__file__).parent / "model_metadata.json").read_text())
        model = FakeEstimator()
        api.model, api.metadata = model, data
        yield http, model, data


def test_health(client):
    http, _, _ = client
    response = http.get("/health")
    assert response.status_code == 200
    assert response.json()["model_loaded"] is True


def test_model_metadata(client):
    http, _, _ = client
    result = http.get("/model/info")
    assert result.status_code == 200
    assert result.json()["version"] == "1.0.0"
    assert len(result.json()["features"]) == 13


def test_prediction_and_order(client):
    http, model, meta = client
    example = HousePredictionRequest.model_json_schema()["example"]
    response = http.post("/predict", json=example)
    assert response.status_code == 200
    assert response.json() == {
        "predicted_price": 480032.65,
        "currency": "USD",
        "model_version": "1.0.0",
    }
    assert model.last_shape == (1, 13)
    assert model.last_values == [example[field] for field in meta["features"]]


def test_negative_bedrooms_rejected(client):
    http, _, _ = client
    example = HousePredictionRequest.model_json_schema()["example"].copy()
    example["beds"] = -1
    response = http.post("/predict", json=example)
    assert response.status_code == 422


def test_unloaded_model_returns_503(client):
    http, _, _ = client
    api.model = None
    response = http.get("/health")
    assert response.status_code == 503
    example = HousePredictionRequest.model_json_schema()["example"]
    assert http.post("/predict", json=example).status_code == 503
