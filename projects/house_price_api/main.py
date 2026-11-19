"""Portfolio-readable adaptation of the user's submitted TripleTen Sprint 10 code.

Keeps the course exercise's startup hook and endpoint behavior for traceability.
"""
from fastapi import FastAPI, HTTPException

from schemas import (
    HousePredictionRequest,
    PredictionResponse,
    ModelInfoResponse,
    HealthCheckResponse,
)
from api import (
    load_model_and_metadata,
    make_prediction,
    get_model_info,
    check_health,
)

app = FastAPI(
    title="House Price Prediction API",
    description="Machine learning service for predicting US apartment prices based on 13 features",
    version="1.0.0",
)


@app.on_event("startup")
async def startup_event():
    success = load_model_and_metadata()
    if not success:
        print("WARNING: Failed to load model at startup")


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    health_status = check_health()
    return HealthCheckResponse(**health_status)


@app.get("/model/info", response_model=ModelInfoResponse)
async def model_info():
    try:
        info = get_model_info()
        return ModelInfoResponse(**info)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: HousePredictionRequest):
    try:
        features_dict = request.model_dump()
        predicted_price = make_prediction(features_dict)
        model_version = get_model_info()["version"]
        return PredictionResponse(
            predicted_price=predicted_price,
            currency="USD",
            model_version=model_version,
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}",
        )


@app.get("/")
async def root():
    return {
        "name": "House Price Prediction API",
        "version": "1.0.0",
        "endpoints": [
            "/health - Check service health",
            "/model/info - Get model information",
            "/predict - Make price prediction",
            "/docs - Interactive API documentation",
        ],
    }
