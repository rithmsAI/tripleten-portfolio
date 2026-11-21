# TripleTen Sprint 11 — Titanic Survival Prediction API

A Docker-based machine-learning project with separate training and serving environments. A random forest predicts Titanic passenger survival, and a FastAPI application serves individual and batch predictions.

## Model results

| Item | Result |
| --- | --- |
| Model | RandomForestClassifier |
| Labeled passengers | 891 |
| Training passengers | 712 |
| Validation passengers | 179 |
| Validation accuracy | 82.68% |
| Split | Stratified 80/20, random_state=42 |

Preprocessing statistics and categorical encoders are learned from the training split only. The API reuses the saved preprocessing settings and encoders.

The reported accuracy comes from one held-out validation split. It is not a Kaggle test-set score.

## Project organization

| Path | Purpose |
| --- | --- |
| training/data/ | Titanic CSV datasets |
| training/train_model.py | Preprocessing, training, evaluation, and artifact creation |
| training/requirements.txt | Training dependencies |
| training/Dockerfile | Training image definition |
| training/models/ | Trained model, encoders, metadata, sample input, and charts |
| serving/app.py | FastAPI prediction service |
| serving/requirements.txt | Serving dependencies |
| serving/requirements-lock.txt | Installed package versions recorded from the tested container |
| serving/Dockerfile | Serving image definition |
| serving/models/ | Model artifacts packaged with the API |

The serving Dockerfile installs requirements.txt. The lock file records the tested environment; it is not currently used by the Dockerfile.

## Data

- train.csv contains labeled passenger records used for training and validation.
- test.csv contains unlabeled competition records.
- gender_submission.csv is an example submission, not ground-truth labels.
- Original downloaded files were preserved.

## Train the model

Prerequisite: Docker Desktop running Linux containers.

Run these PowerShell commands from the titanic-ml-project folder:

```powershell
docker build -t titanic-training:1.0 .\training

$trainingPath = (Resolve-Path .\training).Path

docker run --rm --mount "type=bind,source=$trainingPath,target=/home/jovyan/work" --workdir /home/jovyan/work titanic-training:1.0 python train_model.py
```

Training saves these files in training/models:

- titanic_model.joblib
- label_encoders.joblib
- model_metadata.json
- sample_input.json
- feature_importance.png
- confusion_matrix.png

## Build and run the API

Copy the training artifacts into the serving folder, then build:

```powershell
Copy-Item -Path .\training\models\* -Destination .\serving\models

docker build -t titanic-api:1.0 .\serving
```

Start the API:

```powershell
docker run --rm --name titanic-api -p 127.0.0.1:8000:8000 titanic-api:1.0
```

Keep the terminal running while using the API. Press Ctrl+C to stop it.

- Swagger documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

## Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | / | API welcome message |
| GET | /health | Model-loading status and validation accuracy |
| GET | /model-info | Model metadata and preprocessing settings |
| POST | /predict | Predict one passenger |
| POST | /predict-batch | Predict 1–100 passengers |

## Example prediction request

In Swagger, open POST /predict, select Try it out, and submit:

```json
{
  "Name": "Example, Mr. Passenger",
  "Pclass": 3,
  "Sex": "male",
  "Age": 25.0,
  "SibSp": 0,
  "Parch": 0,
  "Fare": 8.05,
  "Embarked": "S"
}
```

The response contains:

- survived: 0 for predicted non-survival or 1 for predicted survival.
- survival_probability: the model's survival probability estimate.
- prediction_confidence: a category derived from the predicted-class score, not calibrated certainty.
- passenger_profile: the submitted passenger information.

Name is optional and is used to extract the passenger's title. Missing Age, Fare, and Embarked values use the saved training-set replacements.

Batch requests use a JSON array of passenger objects.

## Manual API validation

The following local Swagger checks were completed on November 21, 2026:

| Check | Result |
| --- | --- |
| Health endpoint | Passed: HTTP 200, model loaded |
| Model information | Passed: HTTP 200 |
| Single prediction | Passed: HTTP 200 |
| Two-passenger batch | Passed: two results in input order |
| Single/batch consistency | Passed: matching prediction for the same passenger |
| Negative age | Passed: HTTP 422 |
| Empty batch | Passed: HTTP 422 |
| Missing optional values | Passed: HTTP 200 |

This is an educational model demonstrating training, containerization, validation, and API serving.

## Run the published image

Docker Hub: https://hub.docker.com/r/rithmsai/titanic-api

Available tags: `1.0` and `latest`  
Image platform: `linux/amd64`

```powershell
docker pull rithmsai/titanic-api:1.0

docker run --rm --name titanic-api-published -p 127.0.0.1:8001:8000 rithmsai/titanic-api:1.0
```

Keep the terminal running, then open:

- Health check: http://127.0.0.1:8001/health
- Swagger documentation: http://127.0.0.1:8001/docs

Press Ctrl+C to stop the container.

The published image was pulled and tested locally on November 21, 2026. Its health check and single-passenger prediction returned HTTP 200.