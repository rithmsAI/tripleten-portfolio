"""Serve the trained Titanic model through a FastAPI application."""

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import joblib
import numpy as np
import pandas as pd
import sklearn
from fastapi import Body, FastAPI
from pydantic import BaseModel, ConfigDict, Field


MODELS_DIR = Path(__file__).resolve().parent / "models"


class PassengerInput(BaseModel):
    """Passenger information accepted by the API."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "Name": "Example, Mr. Passenger",
                "Pclass": 3,
                "Sex": "male",
                "Age": 25.0,
                "SibSp": 0,
                "Parch": 0,
                "Fare": 8.05,
                "Embarked": "S",
            }
        },
    )

    Name: str | None = Field(
        default=None,
        max_length=200,
        description="Passenger name including title, such as Mr. or Mrs.",
    )
    Pclass: int = Field(ge=1, le=3, strict=True)
    Sex: Literal["male", "female"]

    Age: float | None = Field(
        default=None,
        ge=0,
        le=120,
        allow_inf_nan=False,
    )

    SibSp: int = Field(
        default=0, ge=0, le=20, strict=True
    )
    Parch: int = Field(
        default=0, ge=0, le=20, strict=True
    )

    Fare: float | None = Field(
        default=None,
        ge=0,
        allow_inf_nan=False,
    )

    Embarked: Literal["C", "Q", "S"] | None = None


class PredictionOutput(BaseModel):
    """Information returned for each prediction."""

    survived: Literal[0, 1]
    survival_probability: float = Field(ge=0, le=1)

    prediction_confidence: Literal["low", "medium", "high"] = Field(
        description=(
            "Model-score category, not calibrated certainty: high >= 0.8, "
            "medium >= 0.6, otherwise low, using the predicted-class score."
        )
    )

    passenger_profile: PassengerInput


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the model once, before accepting requests."""
    required_files = [
        "titanic_model.joblib",
        "label_encoders.joblib",
        "model_metadata.json",
    ]

    missing = [
        name for name in required_files
        if not (MODELS_DIR / name).is_file()
    ]

    if missing:
        raise RuntimeError(
            f"Missing model files: {missing}. "
            "Copy training/models files into serving/models."
        )

    with (MODELS_DIR / "model_metadata.json").open(
        encoding="utf-8"
    ) as file:
        metadata = json.load(file)

    if metadata["sklearn_version"] != sklearn.__version__:
        raise RuntimeError(
            "scikit-learn must match the training version: "
            f"{metadata['sklearn_version']}"
        )

    model = joblib.load(
        MODELS_DIR / "titanic_model.joblib"
    )
    encoders = joblib.load(
        MODELS_DIR / "label_encoders.joblib"
    )

    if list(model.feature_names_in_) != metadata["feature_names"]:
        raise RuntimeError(
            "Model and metadata feature names do not match."
        )

    app.state.model = model
    app.state.encoders = encoders
    app.state.metadata = metadata

    yield


app = FastAPI(
    title="Titanic Survival Prediction API",
    description=(
        "TripleTen Sprint 11: predictions from a trained random forest."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


def prepare_features(data, metadata, encoders):
    """Reproduce training preprocessing using the saved settings."""
    result = data.copy()
    settings = metadata["preprocessing_info"]

    # Fill missing values with the training-set statistics.
    result["Age"] = result["Age"].fillna(
        settings["age_fill_value"]
    )
    result["Fare"] = result["Fare"].fillna(
        settings["fare_fill_value"]
    )
    result["Embarked"] = result["Embarked"].fillna(
        settings["embarked_fill_value"]
    )

    # Recreate family features.
    result["FamilySize"] = (
        result["SibSp"] + result["Parch"] + 1
    )
    result["IsAlone"] = (
        result["FamilySize"] == 1
    ).astype(int)

    # Extract titles exactly as in the training script.
    titles = result["Name"].fillna("").str.extract(
        r" ([A-Za-z]+)\.",
        expand=False,
    )
    titles = titles.replace(settings["title_aliases"])
    titles = titles.replace(
        settings["rare_titles"], "Other"
    )
    result["Title"] = titles.fillna(
        settings["unknown_category"]
    )

    # Recreate age groups.
    result["AgeGroup"] = pd.cut(
        result["Age"],
        bins=[
            -np.inf,
            *settings["age_boundaries"],
            np.inf,
        ],
        labels=settings["age_labels"],
        right=True,
    ).astype(str)

    # Recreate fare groups using the saved training cutoffs.
    fare_indices = np.searchsorted(
        settings["fare_cutoffs"],
        result["Fare"].to_numpy(),
        side="left",
    )
    result["FareGroup"] = np.array(
        settings["fare_labels"]
    )[fare_indices]

    # Apply the saved encoders without fitting them again.
    for column, encoder in encoders.items():
        values = result[column].astype(str)
        values = values.where(
            values.isin(encoder.classes_),
            settings["unknown_category"],
        )
        result[column] = encoder.transform(values)

    # Preserve the exact feature order expected by the model.
    return result[metadata["feature_names"]]


def predict_passengers(passengers):
    """Predict passengers while preserving their input order."""
    data = pd.DataFrame([
        passenger.model_dump()
        for passenger in passengers
    ])

    features = prepare_features(
        data,
        app.state.metadata,
        app.state.encoders,
    )

    model = app.state.model
    predictions = model.predict(features)

    survival_column = list(model.classes_).index(1)
    probabilities = model.predict_proba(
        features
    )[:, survival_column]

    results = []

    for passenger, prediction, probability in zip(
        passengers,
        predictions,
        probabilities,
    ):
        probability = float(probability)

        predicted_class_score = (
            probability
            if int(prediction) == 1
            else 1 - probability
        )

        if predicted_class_score >= 0.8:
            confidence = "high"
        elif predicted_class_score >= 0.6:
            confidence = "medium"
        else:
            confidence = "low"

        results.append(
            PredictionOutput(
                survived=int(prediction),
                survival_probability=probability,
                prediction_confidence=confidence,
                passenger_profile=passenger,
            )
        )

    return results


@app.get("/")
def root():
    return {
        "message": "Titanic Survival Prediction API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "model_loaded": True,
        "model_accuracy": app.state.metadata["accuracy"],
    }


@app.get("/model-info")
def model_info():
    return app.state.metadata


@app.post(
    "/predict",
    response_model=PredictionOutput,
)
def predict(passenger: PassengerInput):
    return predict_passengers([passenger])[0]


@app.post(
    "/predict-batch",
    response_model=list[PredictionOutput],
)
def predict_batch(
    passengers: list[PassengerInput] = Body(
        ..., min_length=1, max_length=100
    ),
):
    return predict_passengers(passengers)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )