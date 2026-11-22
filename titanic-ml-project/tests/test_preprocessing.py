"""Compare training and serving behavior at their independent boundaries."""

from copy import deepcopy

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from pandas.testing import assert_frame_equal
import pytest


def training_features(training, service, data, metadata):
    raw = training.create_features(data, metadata["preprocessing_info"])
    encoded, _ = training.encode_features(raw, service.app.state.encoders)
    return encoded


def test_saved_settings_and_features_match_original_split(
    client, service, training, project_root, metadata
):
    data = pd.read_csv(project_root / "training" / "data" / "train.csv")
    train, validation = train_test_split(
        data, test_size=0.20, random_state=metadata["random_state"], stratify=data["Survived"]
    )
    assert len(train) == metadata["training_rows"]
    assert len(validation) == metadata["validation_rows"]
    fitted = training.fit_preprocessing(train)
    for key, value in fitted.items():
        if isinstance(value, (float, list)):
            np.testing.assert_allclose(value, metadata["preprocessing_info"][key])
        else:
            assert value == metadata["preprocessing_info"][key]

    expected = training_features(training, service, validation, metadata)
    actual = service.prepare_features(validation, metadata, service.app.state.encoders)
    assert_frame_equal(actual, expected)
    assert list(actual.columns) == metadata["feature_names"]
    predictions = service.app.state.model.predict(actual)
    assert (predictions == validation["Survived"].to_numpy()).mean() == pytest.approx(
        metadata["accuracy"]
    )


def test_preprocessing_parity_for_boundaries_missing_values_and_titles(
    client, service, training, metadata, passenger
):
    cases = []
    for age in [0, 12, 12.001, 18, 18.001, 35, 35.001, 60, 60.001, 120, None]:
        cases.append({**passenger, "Age": age})
    for cutoff in metadata["preprocessing_info"]["fare_cutoffs"]:
        for fare in [cutoff - 0.0001, cutoff, cutoff + 0.0001]:
            cases.append({**passenger, "Fare": fare})
    for title in ["Mlle", "Ms", "Mme", "Dr", "Dona", "Unseen"]:
        cases.append({**passenger, "Name": f"Example, {title}. Passenger"})
    cases += [
        {**passenger, "Name": None, "Age": None, "Fare": None, "Embarked": None},
        {**passenger, "Name": "No title", "SibSp": 2, "Parch": 1},
        {**passenger, "Sex": "female", "Embarked": "Q"},
    ]
    data = pd.DataFrame(cases)
    original_data = data.copy(deep=True)
    original_metadata = deepcopy(metadata)
    original_classes = {
        key: encoder.classes_.copy() for key, encoder in service.app.state.encoders.items()
    }
    expected = training_features(training, service, data, metadata)
    actual = service.prepare_features(data, metadata, service.app.state.encoders)
    assert_frame_equal(actual, expected)
    assert_frame_equal(data, original_data)
    assert metadata == original_metadata
    assert not actual.isna().any().any()
    for key, classes in original_classes.items():
        np.testing.assert_array_equal(service.app.state.encoders[key].classes_, classes)


def test_unknown_titles_and_missing_values_use_saved_categories(
    client, service, metadata, passenger
):
    data = pd.DataFrame([
        {**passenger, "Name": None, "Age": None, "Fare": None, "Embarked": None},
        {**passenger, "Name": "Example, Unseen. Passenger", "SibSp": 2, "Parch": 1},
    ])
    features = service.prepare_features(data, metadata, service.app.state.encoders)
    settings = metadata["preprocessing_info"]
    assert features.loc[0, "Age"] == settings["age_fill_value"]
    assert features.loc[0, "Fare"] == settings["fare_fill_value"]
    titles = service.app.state.encoders["Title"].inverse_transform(features["Title"])
    assert list(titles) == ["Unknown", "Unknown"]
    assert list(features["FamilySize"]) == [1, 4]
    assert list(features["IsAlone"]) == [1, 0]


def test_api_predictions_match_training_preprocessing(
    client, service, training, metadata, passenger
):
    cases = [passenger, {**passenger, "Name": "Example, Ms. Passenger", "Sex": "female",
                         "Age": None, "Fare": None, "Embarked": None}]
    features = training_features(training, service, pd.DataFrame(cases), metadata)
    model = service.app.state.model
    expected_labels = model.predict(features)
    expected_probabilities = model.predict_proba(features)[:, list(model.classes_).index(1)]
    response = client.post("/predict-batch", json=cases)
    assert response.status_code == 200
    results = response.json()
    np.testing.assert_array_equal([item["survived"] for item in results], expected_labels)
    np.testing.assert_allclose(
        [item["survival_probability"] for item in results], expected_probabilities,
        rtol=0, atol=1e-12,
    )
