"""Portfolio-readable adaptation of the user's submitted TripleTen Sprint 10 code.

Course instructions and placeholder comments are omitted.
"""
from pydantic import BaseModel, Field


class HousePredictionRequest(BaseModel):
    total_images: int = Field(..., ge=0, le=50, description="Number of property images (0-50)")
    beds: int = Field(..., ge=0, le=10, description="Number of bedrooms (0-10)")
    baths: float = Field(..., ge=0, le=10, description="Number of bathrooms (0-10, can be decimal like 2.5)")
    area: float = Field(..., gt=0, le=10000, description="Property area in square feet (must be positive, max 10000)")
    latitude: float = Field(..., ge=-90, le=90, description="Property latitude (-90 to 90)")
    longitude: float = Field(..., ge=-180, le=180, description="Property longitude (-180 to 180)")
    garden: int = Field(..., ge=0, le=1, description="Has garden: 0=No, 1=Yes")
    garage: int = Field(..., ge=0, le=1, description="Has garage: 0=No, 1=Yes")
    new_construction: int = Field(..., ge=0, le=1, description="Is new construction: 0=No, 1=Yes")
    pool: int = Field(..., ge=0, le=1, description="Has pool: 0=No, 1=Yes")
    terrace: int = Field(..., ge=0, le=1, description="Has terrace: 0=No, 1=Yes")
    air_conditioning: int = Field(..., ge=0, le=1, description="Has AC: 0=No, 1=Yes")
    parking: int = Field(..., ge=0, le=1, description="Has parking: 0=No, 1=Yes")

    class Config:
        json_schema_extra = {
            "example": {
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
                "parking": 1,
            }
        }


class PredictionResponse(BaseModel):
    predicted_price: float = Field(..., description="Predicted house price")
    currency: str = Field(default="USD", description="Currency of the prediction")
    model_version: str = Field(..., description="Version of the model used")


class ModelInfoResponse(BaseModel):
    model_type: str = Field(..., description="Type of machine learning model")
    version: str = Field(..., description="Model version")
    features: list[str] = Field(..., description="Features used by the model")
    training_date: str = Field(..., description="Date when the model was trained")
    rmse: float = Field(..., description="Root mean squared error")
    description: str = Field(..., description="Description of the model")


class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="Service health status")
    model_loaded: bool = Field(..., description="Whether the ML model is loaded")
    message: str = Field(..., description="Description of service status")
