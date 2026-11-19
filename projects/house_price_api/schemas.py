"""Typed input and output contracts for the house-price API."""
from pydantic import BaseModel, ConfigDict, Field


class HousePredictionRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "total_images": 10, "beds": 3, "baths": 2.5, "area": 1800.0,
            "latitude": 40.7128, "longitude": -74.0060, "garden": 1,
            "garage": 1, "new_construction": 0, "pool": 0,
            "terrace": 1, "air_conditioning": 1, "parking": 1,
        }
    })

    total_images: int = Field(ge=0, le=50)
    beds: int = Field(ge=0, le=10)
    baths: float = Field(ge=0, le=10)
    area: float = Field(gt=0, le=10000)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    garden: int = Field(ge=0, le=1)
    garage: int = Field(ge=0, le=1)
    new_construction: int = Field(ge=0, le=1)
    pool: int = Field(ge=0, le=1)
    terrace: int = Field(ge=0, le=1)
    air_conditioning: int = Field(ge=0, le=1)
    parking: int = Field(ge=0, le=1)


class PredictionResponse(BaseModel):
    predicted_price: float = Field(description="Predicted price in USD")
    currency: str = Field(default="USD")
    model_version: str


class ModelInfoResponse(BaseModel):
    model_type: str
    version: str
    features: list[str]
    training_date: str
    rmse: float
    description: str


class HealthCheckResponse(BaseModel):
    status: str
    model_loaded: bool
    message: str
