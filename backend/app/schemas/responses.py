"""Response schemas for ORCA API."""

from typing import Any
from pydantic import BaseModel, Field


class LocationData(BaseModel):
    location_name: str
    requested_latitude: float
    requested_longitude: float
    grid_latitude: float | None = None
    grid_longitude: float | None = None


class TimeSeriesPoint(BaseModel):
    timestamp: str
    wave_height: float | None = None


class MeasurementsData(BaseModel):
    variable: str = "wave_height"
    unit: str = "m"
    sample_count: int
    min_wave_height_m: float | None = None
    max_wave_height_m: float | None = None
    avg_wave_height_m: float | None = None
    latest_wave_height_m: float | None = None
    timeseries: list[TimeSeriesPoint] = Field(default_factory=list)


class TimestampsData(BaseModel):
    retrieved_at: str
    forecast_start: str | None = None
    forecast_end: str | None = None
    forecast_time_window_hours: int


class SourceData(BaseModel):
    provider: str = "open-meteo-marine"
    model_timezone: str = "GMT"
    attribution: str = "Open-Meteo Marine Weather API (ECMWF / Meteo-France models)"
    citation: str = "WMO Code Table 3700 / Douglas Sea Scale; Open-Meteo API (https://open-meteo.com/)"


class ValidationStatusData(BaseModel):
    status: str  # "valid", "insufficient_evidence", "evidence_requires_review"
    is_valid: bool
    issues: list[str] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)
    records_analyzed: int


class AnalysisData(BaseModel):
    sea_state_code: int | None = None
    sea_state_category: str
    rule_standard: str
    advisory: str
    generation_mode: str  # "deterministic" or "llm"


class OrcaAnalyzeResponse(BaseModel):
    agent_name: str = "ORCA Marine Intelligence Agent"
    workflow_id: str
    status: str
    location: LocationData
    measurements: MeasurementsData
    units: dict[str, str]
    timestamps: TimestampsData
    source: SourceData
    validation_status: ValidationStatusData
    analysis: AnalysisData
    limitations: list[str]
    step_progress: list[str] = Field(default_factory=list)
