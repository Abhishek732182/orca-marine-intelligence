"""Request schemas for ORCA API."""

from pydantic import BaseModel, Field


class OrcaAnalyzeRequest(BaseModel):
    """Input request for the ORCA Marine Intelligence Agent."""

    location_name: str = Field(
        default="Offshore Marine Location",
        description="Human-readable name or label of the marine location",
        min_length=1,
        max_length=200,
    )
    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Latitude between -90 and 90 degrees",
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Longitude between -180 and 180 degrees",
    )
    forecast_time_window_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Forecast time window in hours (1 to 168 hours)",
    )
