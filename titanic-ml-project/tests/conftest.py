"""Load the actual application and saved model without retraining anything."""

import importlib.util
import json
from pathlib import Path
import sys
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_module(path, prefix):
    name = f"{prefix}_{uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def project_root():
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def service():
    return load_module(PROJECT_ROOT / "serving" / "app.py", "titanic_api")


@pytest.fixture(scope="session")
def training():
    # Importing this module does not call main() or rewrite saved artifacts.
    return load_module(PROJECT_ROOT / "training" / "train_model.py", "titanic_training")


@pytest.fixture(scope="session")
def metadata():
    path = PROJECT_ROOT / "serving" / "models" / "model_metadata.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def client(service):
    # Enter the context to execute lifespan and load the real saved model.
    with TestClient(service.app) as test_client:
        yield test_client


@pytest.fixture
def passenger():
    return {
        "Name": "Example, Mr. Passenger",
        "Pclass": 3,
        "Sex": "male",
        "Age": 25.0,
        "SibSp": 0,
        "Parch": 0,
        "Fare": 8.05,
        "Embarked": "S",
    }


@pytest.fixture
def fresh_service():
    return load_module(PROJECT_ROOT / "serving" / "app.py", "titanic_startup")


@pytest.fixture(scope="session")
def healthcheck():
    return load_module(PROJECT_ROOT / "serving" / "healthcheck.py", "titanic_healthcheck")
