"""Train and evaluate the Titanic model, then save its artifacts."""

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# Save charts without opening a window inside Docker.
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# Paths are relative to this script.
BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "train.csv"
MODELS_DIR = BASE_DIR / "models"

FEATURES = [
    "Pclass", "Sex", "Age", "SibSp", "Parch", "Fare", "Embarked",
    "FamilySize", "IsAlone", "Title", "AgeGroup", "FareGroup",
]

CATEGORICAL_FEATURES = [
    "Sex", "Embarked", "Title", "AgeGroup", "FareGroup",
]

AGE_LABELS = ["Child", "Teen", "Adult", "Middle", "Senior"]
FARE_LABELS = ["Low", "Medium", "High", "VeryHigh"]

TITLE_ALIASES = {
    "Mlle": "Miss",
    "Ms": "Miss",
    "Mme": "Mrs",
}

RARE_TITLES = [
    "Lady", "Countess", "Capt", "Col", "Don", "Dr",
    "Major", "Rev", "Sir", "Jonkheer", "Dona",
]


def fit_preprocessing(training_data):
    """Learn missing-value replacements and fare cutoffs."""
    age_median = float(training_data["Age"].median())
    fare_median = float(training_data["Fare"].median())
    embarked_mode = str(training_data["Embarked"].mode().iloc[0])

    fares = training_data["Fare"].fillna(fare_median)

    return {
        "age_fill_value": age_median,
        "fare_fill_value": fare_median,
        "embarked_fill_value": embarked_mode,
        "fare_cutoffs": np.quantile(
            fares, [0.25, 0.50, 0.75]
        ).tolist(),
    }


def create_features(data, settings):
    """Apply saved preprocessing settings and create features."""
    result = data.copy()

    # Fill missing values using training-set statistics.
    result["Age"] = result["Age"].fillna(
        settings["age_fill_value"]
    )
    result["Fare"] = result["Fare"].fillna(
        settings["fare_fill_value"]
    )
    result["Embarked"] = result["Embarked"].fillna(
        settings["embarked_fill_value"]
    )

    # Family-related features.
    result["FamilySize"] = result["SibSp"] + result["Parch"] + 1
    result["IsAlone"] = (result["FamilySize"] == 1).astype(int)

    # Extract and simplify passenger titles.
    titles = result["Name"].str.extract(
        r" ([A-Za-z]+)\.", expand=False
    )
    titles = titles.replace(TITLE_ALIASES)
    titles = titles.replace(RARE_TITLES, "Other")
    result["Title"] = titles.fillna("Unknown")

    # Create age groups.
    result["AgeGroup"] = pd.cut(
        result["Age"],
        bins=[-np.inf, 12, 18, 35, 60, np.inf],
        labels=AGE_LABELS,
        right=True,
    ).astype(str)

    # Create fare groups using training-set cutoffs.
    fare_indices = np.searchsorted(
        settings["fare_cutoffs"],
        result["Fare"].to_numpy(),
        side="left",
    )
    result["FareGroup"] = np.array(FARE_LABELS)[fare_indices]

    return result[FEATURES].copy()


def encode_features(features, encoders=None):
    """Fit categorical encoders or reuse existing encoders."""
    result = features.copy()
    fitting = encoders is None

    if fitting:
        encoders = {}

    for column in CATEGORICAL_FEATURES:
        values = result[column].astype(str)

        if fitting:
            encoder = LabelEncoder()
            encoder.fit(values.tolist() + ["Unknown"])
            encoders[column] = encoder

        encoder = encoders[column]

        # Handle categories absent from the training split.
        values = values.where(
            values.isin(encoder.classes_), "Unknown"
        )
        result[column] = encoder.transform(values)

    return result, encoders


def save_plots(model, y_valid, predictions):
    """Save feature importance and confusion matrix charts."""
    importance = pd.Series(
        model.feature_importances_,
        index=FEATURES,
    ).sort_values()

    fig, ax = plt.subplots(figsize=(9, 6))
    importance.plot.barh(ax=ax)
    ax.set_title("Titanic model: feature importance")
    ax.set_xlabel("Importance")
    fig.tight_layout()
    fig.savefig(
        MODELS_DIR / "feature_importance.png",
        dpi=200,
    )
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 5))
    ConfusionMatrixDisplay.from_predictions(
        y_valid,
        predictions,
        labels=[0, 1],
        display_labels=["Did not survive", "Survived"],
        cmap="Blues",
        ax=ax,
        colorbar=False,
    )
    ax.set_title("Validation confusion matrix")
    fig.tight_layout()
    fig.savefig(
        MODELS_DIR / "confusion_matrix.png",
        dpi=200,
    )
    plt.close(fig)


def main():
    # Load the labeled dataset.
    if not DATA_PATH.is_file():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}"
        )

    data = pd.read_csv(DATA_PATH)

    required_columns = {
        "Survived", "Name", "Pclass", "Sex", "Age",
        "SibSp", "Parch", "Fare", "Embarked",
    }
    missing_columns = required_columns.difference(data.columns)

    if missing_columns:
        raise ValueError(
            f"Missing columns: {sorted(missing_columns)}"
        )

    print(
        f"Loaded {len(data)} passengers from {DATA_PATH.name}"
    )

    # Split before learning any preprocessing statistics.
    training_data, validation_data = train_test_split(
        data,
        test_size=0.20,
        random_state=42,
        stratify=data["Survived"],
    )

    settings = fit_preprocessing(training_data)

    X_train, encoders = encode_features(
        create_features(training_data, settings)
    )
    X_valid, _ = encode_features(
        create_features(validation_data, settings),
        encoders,
    )

    y_train = training_data["Survived"]
    y_valid = validation_data["Survived"]

    # Train the random forest.
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
    )
    model.fit(X_train, y_train)

    # Evaluate on passengers excluded from training.
    predictions = model.predict(X_valid)
    accuracy = float(
        accuracy_score(y_valid, predictions)
    )

    print(f"Training rows: {len(X_train)}")
    print(f"Validation rows: {len(X_valid)}")
    print(f"Validation accuracy: {accuracy:.2%}")
    print(
        classification_report(
            y_valid,
            predictions,
            zero_division=0,
        )
    )

    # Save the evaluated model and its encoders.
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    joblib.dump(
        model,
        MODELS_DIR / "titanic_model.joblib",
    )
    joblib.dump(
        encoders,
        MODELS_DIR / "label_encoders.joblib",
    )

    # Save information needed to reproduce preprocessing.
    metadata = {
        "model_type": "RandomForestClassifier",
        "training_date": datetime.now(timezone.utc).isoformat(),
        "accuracy": accuracy,
        "feature_names": FEATURES,
        "model_parameters": model.get_params(),
        "training_rows": len(X_train),
        "validation_rows": len(X_valid),
        "random_state": 42,
        "sklearn_version": sklearn.__version__,
        "preprocessing_info": {
            **settings,
            "age_boundaries": [12, 18, 35, 60],
            "age_labels": AGE_LABELS,
            "fare_labels": FARE_LABELS,
            "title_aliases": TITLE_ALIASES,
            "rare_titles": RARE_TITLES,
            "unknown_category": "Unknown",
            "new_features": [
                "FamilySize",
                "IsAlone",
                "Title",
                "AgeGroup",
                "FareGroup",
            ],
        },
    }

    with (MODELS_DIR / "model_metadata.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(
            metadata,
            file,
            indent=2,
            allow_nan=False,
        )

    sample_input = {
        "Name": "Example, Mr. Passenger",
        "Pclass": 3,
        "Sex": "male",
        "Age": 25.0,
        "SibSp": 0,
        "Parch": 0,
        "Fare": 8.05,
        "Embarked": "S",
    }

    with (MODELS_DIR / "sample_input.json").open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(sample_input, file, indent=2)

    save_plots(model, y_valid, predictions)

    print(
        f"Model artifacts and charts saved to: {MODELS_DIR}"
    )


if __name__ == "__main__":
    main()