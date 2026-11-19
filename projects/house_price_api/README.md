# House Price Prediction API — Sprint 10 Portfolio Case Study

**Status:** Educational FastAPI implementation and documented local coursework. The portfolio code is a separately reconstructed implementation based on the completed Sprint 10 workflow; it is **not** represented as an exact export of the student's final local ZIP. Its API interface has been tested offline with a stand-in estimator. The original trained `model.pkl` is **not** distributed here.

[Portfolio case study](./index.html) · [Back to portfolio](../../README.md)

## What the project demonstrates

- A FastAPI service with `GET /health`, `GET /model/info` and `POST /predict`.
- Pydantic v2 validation for 13 ordered house-property features and typed response contracts.
- Loading the model and its metadata at application startup rather than per prediction request.
- Enforcing the feature order defined in the metadata before constructing a NumPy array with shape `(1, 13)`.
- Returning explicit HTTP 422 for invalid inputs and 503 when the model is unavailable.
- Interactive OpenAPI/Swagger documentation at `/docs`.

The coursework was locally executed in VS Code using Python 3.12 and scikit-learn 1.5.1. The user reported that the example property produced **$480,032.65**; this observation is **not** an independent performance or accuracy benchmark. A negative bedroom count was rejected with HTTP 422. The course project was submitted separately to TripleTen for review.

## Project files

| File | Purpose |
| --- | --- |
| `schemas.py` | Input and output Pydantic contracts |
| `api.py` | Model loading, feature ordering, prediction and health operations |
| `main.py` | FastAPI routes and startup lifecycle |
| `model_metadata.json` | Model information and ordered list of 13 features |
| `requirements.txt` | Suggested matching Python 3.12 dependencies |
| `test_service.py` | Offline tests using a simulated estimator (no supplied course model) |

## Run locally

Use **Python 3.12**. From this directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

Obtain the original `model.pkl` from the authorized TripleTen course materials or your own saved Sprint 10 submission and place it alongside `main.py`. **Do not deserialize untrusted model files:** joblib/pickle loading can execute code. The model was saved with scikit-learn **1.5.1** and compatibility depends on using suitable library versions.

```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

Open `http://127.0.0.1:8001/docs`. The application can start without the model, but `/health` will respond 503 and `/predict` will be unavailable until a trusted model artifact is installed and the service restarted.

### Example request

```json
{
  "total_images": 10,
  "beds": 3,
  "baths": 2.5,
  "area": 1800.0,
  "latitude": 40.7128,
  "longitude": -74.0060,
  "garden": 1,
  "garage": 1,
  "new_construction": 0,
  "pool": 0,
  "terrace": 1,
  "air_conditioning": 1,
  "parking": 1
}
```

The `POST /predict` response is a JSON object containing `predicted_price`, `currency` and `model_version`. An example value such as `480032.65` is model-dependent, not a guaranteed value in every environment.

## Testing

```powershell
python -m pytest -q test_service.py
```

Five offline tests check health reporting, metadata fields and feature count, feature ordering and prediction response, rejection of invalid bedroom counts (422), and unavailable-model behavior (503). These tests use a **fake estimator** and do not validate real-world predictive accuracy. At the time this portfolio update was prepared, those five tests passed in an available Python test environment. The exact pinned dependency combination and an end-to-end run using the course's original model were **not** reverified in that environment.

## Provenance, permissions and limits

This is a **TripleTen educational project**, based on a course-provided starter and trained artifact, completed and tested locally by the learner with AI-assisted guidance. This public portfolio implementation was separately reconstructed for documentation and review; the exact edited local submission is not claimed to be published here. The archive's course-supplied `model.pkl` is intentionally excluded until redistribution rights are confirmed. The model metadata is provided for explanatory and interoperability purposes.

No production deployment, external users, authentication, tenancy, accuracy guarantee, or real estate appraisal suitability is claimed. Before production use, review licensing, model evaluation and drift, input provenance, endpoint authentication, operational monitoring, deployment security, and inference reproducibility. The code is meant for local educational inspection.
