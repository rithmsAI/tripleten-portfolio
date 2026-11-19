"""Offline tests derived from the user's completed Sprint 10 submission.

These do not deserialize or redistribute the course model artifact.
"""
import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

import api
from main import app
from schemas import HousePredictionRequest


class StandInModel:
    def __init__(self):
        self.shape = None
        self.values = None

    def predict(self, features):
        self.shape = features.shape
        self.values = features[0].tolist()
        return np.array([480032.65])


@pytest.fixture
def context(monkeypatch):
    model_metadata = json.loads(
        Path(__file__).with_name("model_metadata.json").read_text(encoding="utf-8")
    )
    standin = StandInModel()
    monkeypatch.setattr(api, "model", standin)
    monkeypatch.setattr(api, "metadata", model_metadata)
    # No TestClient context manager: startup should not load the course model.
    return TestClient(app), standin, model_metadata


def example():
    return HousePredictionRequest.model_json_schema()["example"].copy()


def test_health(context):
    client, _, _ = context
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["model_loaded"] is True


def test_model_metadata(context):
    client, _, _ = context
    result = client.get("/model/info")
    assert result.status_code == 200
    assert result.json()["model_type"] == "RandomForestRegressor"
    assert len(result.json()["features"]) == 13


def test_prediction_and_feature_order(context):
    client, model, metadata = context
    payload = example()
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    assert response.json() == {
        "predicted_price": 480032.65,
        "currency": "USD",
        "model_version": "1.0.0",
    }
    assert model.shape == (1, 13)
    assert model.values == [payload[field] for field in metadata["features"]]


def test_negative_bedrooms_rejected(context):
    client, _, _ = context
    payload = example()
    payload["beds"] = -1
    response = client.post("/predict", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "beds"]


def test_unavailable_model_and_metadata(context, monkeypatch):
    client, _, _ = context
    monkeypatch.setattr(api, "model", None)
    assert client.post("/predict", json=example()).status_code == 503
    health = client.get("/health")
    # The student's submitted implementation reports unhealthy in the JSON body.
    assert health.status_code == 200
    assert health.json()["status"] == "unhealthy"
    monkeypatch.setattr(api, "metadata", None)
    assert client.get("/model/info").status_code == 503
