"""Fail closed when saved artifacts cannot support consistent inference."""

import json
import shutil

from fastapi.testclient import TestClient
import pytest


def test_missing_model_files_prevent_startup(fresh_service, tmp_path, monkeypatch):
    monkeypatch.setattr(fresh_service, "MODELS_DIR", tmp_path)
    with pytest.raises(RuntimeError, match="Missing model files"):
        with TestClient(fresh_service.app):
            pass


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [("sklearn_version", "0.0.0", "scikit-learn must match"),
     ("feature_names", ["wrong_feature"], "feature names do not match")],
)
def test_incompatible_metadata_prevents_startup(
    fresh_service, tmp_path, monkeypatch, field, value, message
):
    for source in fresh_service.MODELS_DIR.iterdir():
        if source.is_file():
            shutil.copy2(source, tmp_path / source.name)
    metadata_path = tmp_path / "model_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata[field] = value
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    monkeypatch.setattr(fresh_service, "MODELS_DIR", tmp_path)
    with pytest.raises(RuntimeError, match=message):
        with TestClient(fresh_service.app):
            pass
