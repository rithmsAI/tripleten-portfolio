"""FastAPI endpoints for a versioned, local house-price prediction service."""
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException, Response

import api
from schemas import (
    HealthCheckResponse,
    HousePredictionRequest,
    ModelInfoResponse,
    PredictionResponse,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    if not api.load_model_and_metadata():
        logger.warning("Prediction model unavailable; see README for local setup")
    yield
    api.model = None
    api.metadata = None


app = FastAPI(
    title="House Price Prediction API",
    description="Local educational inference service for 13 apartment features.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthCheckResponse, tags=["Status"])
def health_check(response: Response):
    health = api.check_health()
    if health["status"] != "healthy":
        response.status_code = 503
    return HealthCheckResponse.model_validate(health)


@app.get("/model/info", response_model=ModelInfoResponse, tags=["Models"])
def model_info():
    try:
        return ModelInfoResponse.model_validate(api.get_model_info())
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/predict", response_model=PredictionResponse, tags=["Predictions"])
def predict(request: HousePredictionRequest):
    try:
        prediction = api.make_prediction(request.model_dump())
        version = api.get_model_info()["version"]
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail="Prediction failed") from exc
    return PredictionResponse(predicted_price=prediction, model_version=version)


@app.get("/", tags=["Status"])
def root():
    return {"service": "House Price Prediction API", "version": "1.0.0", "docs": "/docs"}
