"""HTTP contracts exercised with the trained, serialized random forest."""

import pytest


def assert_prediction(result):
    assert set(result) == {
        "survived", "survival_probability", "prediction_confidence", "passenger_profile"
    }
    assert result["survived"] in (0, 1)
    assert 0 <= result["survival_probability"] <= 1
    assert result["prediction_confidence"] in {"low", "medium", "high"}


def test_health_and_model_information(client, metadata):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["model_loaded"] is True
    assert response.json()["model_accuracy"] == metadata["accuracy"]
    response = client.get("/model-info")
    assert response.status_code == 200
    assert response.json() == metadata


def test_single_prediction_has_documented_contract(client, passenger):
    response = client.post("/predict", json=passenger)
    assert response.status_code == 200
    result = response.json()
    assert_prediction(result)
    assert result["passenger_profile"] == passenger
    assert client.post("/predict", json=passenger).json() == result


def test_batch_matches_single_requests_and_preserves_input_order(client, passenger):
    passengers = [
        passenger,
        {**passenger, "Name": "Example, Mrs. Passenger", "Sex": "female", "Pclass": 1,
         "Age": 38.0, "Fare": 71.2833, "SibSp": 1, "Embarked": "C"},
        {"Pclass": 2, "Sex": "female", "Age": None, "Fare": None, "Embarked": None},
    ]
    expected = []
    for item in passengers:
        response = client.post("/predict", json=item)
        assert response.status_code == 200
        expected.append(response.json())
    response = client.post("/predict-batch", json=passengers)
    assert response.status_code == 200
    assert response.json() == expected
    reversed_response = client.post("/predict-batch", json=list(reversed(passengers)))
    assert reversed_response.status_code == 200
    assert reversed_response.json() == list(reversed(expected))


@pytest.mark.parametrize("size", [1, 100])
def test_allowed_batch_size_boundaries(client, passenger, size):
    response = client.post("/predict-batch", json=[passenger] * size)
    assert response.status_code == 200
    assert len(response.json()) == size
    assert all(item == response.json()[0] for item in response.json())


@pytest.mark.parametrize("size", [0, 101])
def test_disallowed_batch_size_boundaries(client, passenger, size):
    response = client.post("/predict-batch", json=[passenger] * size)
    assert response.status_code == 422


def test_invalid_item_rejects_entire_batch(client, passenger):
    response = client.post("/predict-batch", json=[passenger, {**passenger, "Age": -1}])
    assert response.status_code == 422
    assert any(error["loc"][:2] == ["body", 1] for error in response.json()["detail"])


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("Age", -1), ("Age", 121), ("Age", "NaN"), ("Age", "Infinity"),
        ("Fare", -0.01), ("Fare", "Infinity"),
        ("Pclass", 0), ("Pclass", 4), ("Pclass", "3"), ("Pclass", True),
        ("Sex", "unknown"), ("Embarked", "X"),
        ("SibSp", -1), ("SibSp", 21), ("SibSp", 1.5),
        ("Parch", -1), ("Parch", 21), ("Parch", "0"),
        ("Name", "X" * 201), ("unrecognized_field", 1),
    ],
)
def test_invalid_fields_return_422(client, passenger, field, value):
    response = client.post("/predict", json={**passenger, field: value})
    assert response.status_code == 422
    assert any(field in error["loc"] for error in response.json()["detail"])


@pytest.mark.parametrize("required_field", ["Pclass", "Sex"])
def test_missing_required_fields_return_422(client, passenger, required_field):
    passenger.pop(required_field)
    response = client.post("/predict", json=passenger)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload", [None, [], "passenger", {"Pclass": 1, "Sex": "female", "Name": 123}]
)
def test_invalid_request_shapes_return_422(client, payload):
    assert client.post("/predict", json=payload).status_code == 422


def test_batch_requires_a_json_array(client, passenger):
    assert client.post("/predict-batch", json=passenger).status_code == 422


def test_missing_optional_values_use_saved_defaults(client):
    minimal = {"Pclass": 3, "Sex": "male"}
    explicit = {**minimal, "Name": None, "Age": None, "Fare": None,
                "Embarked": None, "SibSp": 0, "Parch": 0}
    omitted = client.post("/predict", json=minimal)
    nulls = client.post("/predict", json=explicit)
    assert omitted.status_code == nulls.status_code == 200
    assert_prediction(omitted.json())
    assert omitted.json() == nulls.json()
    # The response reports the submitted profile, not the filled training values.
    assert nulls.json()["passenger_profile"]["Age"] is None


@pytest.mark.parametrize("age", [0, 120])
def test_valid_numeric_boundaries_are_accepted(client, passenger, age):
    response = client.post("/predict", json={**passenger, "Age": age, "Fare": 0,
                                            "SibSp": 20, "Parch": 20})
    assert response.status_code == 200
    assert_prediction(response.json())


def test_openapi_documents_both_prediction_endpoints(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "post" in paths["/predict"]
    assert "post" in paths["/predict-batch"]
    assert "requestBody" in paths["/predict-batch"]["post"]
