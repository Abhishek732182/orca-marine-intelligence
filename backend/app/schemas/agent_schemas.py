"""Pydantic request and response schemas for ORCA's five independent agents."""

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field, model_validator


# ==============================================================================
# Agent 1: Weather Agent Schemas
# ==============================================================================

class WeatherAnalyzeRequest(BaseModel):
    """Input request for Weather Agent."""

    location_name: str | None = Field(
        default=None,
        description="Location name (e.g., 'Goa', 'Mumbai Port', 'Arabian Sea')",
        max_length=200,
    )
    latitude: float | None = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="Latitude between -90 and 90 degrees",
    )
    longitude: float | None = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        description="Longitude between -180 and 180 degrees",
    )
    forecast_days: int = Field(
        default=1,
        ge=1,
        le=7,
        description="Number of forecast days (1 to 7)",
    )


class WeatherForecastItem(BaseModel):
    timestamp: str
    temperature_c: float | None = None
    wind_speed_kmh: float | None = None
    wind_speed_knots: float | None = None
    wind_direction_deg: float | None = None
    precipitation_mm: float | None = None


class WeatherAnalyzeResponse(BaseModel):
    """Response schema for Weather Agent."""

    agent: str = "Weather Agent"
    status: str  # "success", "insufficient_evidence", "error"
    location: dict[str, Any]
    data_source: dict[str, Any]
    observations: dict[str, Any]
    forecast: list[WeatherForecastItem] = Field(default_factory=list)
    analysis: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    error: str | None = None


# ==============================================================================
# Agent 2: Ocean Agent Schemas
# ==============================================================================

class OceanAnalyzeRequest(BaseModel):
    """Input request for Ocean Agent."""

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
    location_name: str = Field(
        default="Offshore Marine Location",
        description="Human-readable marine location label",
        max_length=200,
    )
    forecast_time_window_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Forecast time window in hours (1 to 168)",
    )


class OceanTimeSeriesPoint(BaseModel):
    timestamp: str
    wave_height_m: float | None = None


class OceanAnalyzeResponse(BaseModel):
    """Response schema for Ocean Agent."""

    agent: str = "Ocean Agent"
    status: str  # "success", "insufficient_evidence", "error"
    location: dict[str, Any]
    data_source: dict[str, Any]
    observations: dict[str, Any]
    analysis: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    error: str | None = None


# ==============================================================================
# Agent 3: Fishing Zone Agent Schemas
# ==============================================================================

class FishingZoneAnalyzeRequest(BaseModel):
    """Input request for Fishing Zone Agent."""

    latitude: float | None = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="Latitude between -90 and 90 degrees",
    )
    longitude: float | None = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        description="Longitude between -180 and 180 degrees",
    )
    location_name: str | None = Field(
        default=None,
        description="Location name",
        max_length=200,
    )
    forecast_time_window_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Forecast time window in hours",
    )
    target_species: str | None = Field(
        default=None,
        description="Target fish species (e.g., Mackerel, Tuna, Sardine)",
        max_length=100,
    )


class FishingZoneAnalyzeResponse(BaseModel):
    """Response schema for Fishing Zone Agent."""

    agent: str = "Fishing Zone Agent"
    status: str  # "success", "insufficient_evidence", "error"
    location: dict[str, Any] | None = None
    data_source: dict[str, Any]
    observations: dict[str, Any]
    analysis: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    error: str | None = None


# ==============================================================================
# Agent 4: Route Agent Schemas
# ==============================================================================

class WaypointItem(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    name: str | None = Field(default=None, max_length=100)


class RouteAnalyzeRequest(BaseModel):
    """Input request for Route Agent."""

    origin_latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Origin latitude (-90 to 90)",
    )
    origin_longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Origin longitude (-180 to 180)",
    )
    destination_latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Destination latitude (-90 to 90)",
    )
    destination_longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Destination longitude (-180 to 180)",
    )
    origin_name: str | None = Field(
        default="Origin Point",
        max_length=150,
    )
    destination_name: str | None = Field(
        default="Destination Point",
        max_length=150,
    )
    waypoints: list[WaypointItem] = Field(
        default_factory=list,
        description="Optional ordered intermediate waypoints",
    )
    vessel_speed_knots: float = Field(
        default=12.0,
        gt=0.0,
        le=60.0,
        description="Estimated cruising speed in knots (1 to 60)",
    )


class RouteLeg(BaseModel):
    from_name: str
    to_name: str
    from_lat: float
    from_lon: float
    to_lat: float
    to_lon: float
    distance_km: float
    distance_nm: float
    initial_bearing_deg: float


class RouteGeometryPoint(BaseModel):
    latitude: float
    longitude: float
    leg_index: int


class RouteAnalyzeResponse(BaseModel):
    """Response schema for Route Agent."""

    agent: str = "Route Agent"
    status: str  # "success", "error"
    location: dict[str, Any]
    data_source: dict[str, Any]
    observations: dict[str, Any]
    analysis: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    error: str | None = None


# ==============================================================================
# Agent 5: Safety/Risk Agent Schemas
# ==============================================================================

class SafetyRiskAnalyzeRequest(BaseModel):
    """Input request for Safety/Risk Agent."""

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
    location_name: str | None = Field(
        default="Offshore Location",
        max_length=200,
    )
    vessel_type: str = Field(
        default="small_craft",
        description="Vessel type: 'small_craft', 'trawler', 'commercial_cargo', or 'passenger'",
    )
    wave_height_m: float | None = Field(
        default=None,
        ge=0.0,
        description="Optional observed significant wave height in meters",
    )
    wind_speed_knots: float | None = Field(
        default=None,
        ge=0.0,
        description="Optional observed wind speed in knots",
    )
    precipitation_mm: float | None = Field(
        default=None,
        ge=0.0,
        description="Optional observed precipitation rate in mm/h",
    )


class SafetyRiskAnalyzeResponse(BaseModel):
    """Response schema for Safety/Risk Agent."""

    agent: str = "Safety/Risk Agent"
    status: str  # "success", "insufficient_evidence", "error"
    location: dict[str, Any]
    data_source: dict[str, Any]
    observations: dict[str, Any]
    analysis: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    error: str | None = None


# ==============================================================================
# Agent 6: Orchestrator Agent Schemas
# ==============================================================================

class OrchestratorAnalyzeRequest(BaseModel):
    """Input request for ORCA Orchestrator Agent."""

    latitude: float | None = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="Origin latitude (-90.0 to 90.0)",
    )
    longitude: float | None = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        description="Origin longitude (-180.0 to 180.0)",
    )
    origin_latitude: float | None = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="Explicit origin latitude (-90.0 to 90.0)",
    )
    origin_longitude: float | None = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        description="Explicit origin longitude (-180.0 to 180.0)",
    )
    location_name: str | None = Field(
        default="Marine Operational Area",
        max_length=200,
        description="Origin or operating location name",
    )
    origin_name: str | None = Field(
        default=None,
        max_length=200,
        description="Explicit origin location name",
    )
    forecast_time_window_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Forecast time window in hours (1 to 168)",
    )
    user_objective: str = Field(
        default="general_maritime",
        description="Mission objective: 'general_maritime', 'fishing', 'passage_planning', 'safety_check', or 'all'",
    )
    vessel_type: str = Field(
        default="small_craft",
        description="Vessel type: 'small_craft', 'trawler', 'commercial_cargo', or 'passenger'",
    )
    target_species: str | None = Field(
        default=None,
        max_length=100,
        description="Target fish species (e.g., 'Mackerel', 'Tuna', 'Sardine')",
    )
    destination_latitude: float | None = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="Optional destination latitude (-90.0 to 90.0) for route planning",
    )
    destination_longitude: float | None = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        description="Optional destination longitude (-180.0 to 180.0) for route planning",
    )
    destination_name: str | None = Field(
        default=None,
        max_length=150,
        description="Optional destination name",
    )
    waypoints: list[WaypointItem] = Field(
        default_factory=list,
        description="Optional ordered intermediate waypoints for passage planning",
    )
    vessel_speed_knots: float = Field(
        default=12.0,
        gt=0.0,
        le=60.0,
        description="Estimated cruising speed in knots",
    )
    # Optional in-situ manual observations passed to specialist agents
    wave_height_m: float | None = Field(
        default=None,
        ge=0.0,
        description="Optional observed significant wave height in meters",
    )
    wind_speed_knots: float | None = Field(
        default=None,
        ge=0.0,
        description="Optional observed wind speed in knots",
    )
    precipitation_mm: float | None = Field(
        default=None,
        ge=0.0,
        description="Optional observed precipitation in mm/h",
    )
    query: str | None = Field(
        default=None,
        description="Optional natural-language mission query or prompt for LLM-based planning and synthesis",
    )
    message: str | None = Field(
        default=None,
        description="Alias for query",
    )

    @model_validator(mode="before")
    @classmethod
    def reconcile_origin_and_destination(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Normalize query alias
            if data.get("message") and not data.get("query"):
                data["query"] = data["message"]

            query_text = data.get("query")
            # If coordinates are missing but a natural-language query is provided, attempt extraction
            if query_text and (data.get("latitude") is None and data.get("origin_latitude") is None):
                from app.agents.mission_planner import _extract_location_and_endpoints
                t_olat, t_olon, t_oname, t_dlat, t_dlon, t_dname = _extract_location_and_endpoints(query_text)
                if t_olat is not None and t_olon is not None:
                    data["latitude"] = t_olat
                    data["longitude"] = t_olon
                    data["origin_latitude"] = t_olat
                    data["origin_longitude"] = t_olon
                    if t_oname and not data.get("origin_name"):
                        data["origin_name"] = t_oname
                        data["location_name"] = t_oname
                if t_dlat is not None and t_dlon is not None and data.get("destination_latitude") is None:
                    data["destination_latitude"] = t_dlat
                    data["destination_longitude"] = t_dlon
                    if t_dname and not data.get("destination_name"):
                        data["destination_name"] = t_dname

            # 1. Map origin fields
            if data.get("origin_latitude") is not None and data.get("latitude") is None:
                data["latitude"] = data["origin_latitude"]
            elif data.get("latitude") is not None and data.get("origin_latitude") is None:
                data["origin_latitude"] = data["latitude"]

            if data.get("origin_longitude") is not None and data.get("longitude") is None:
                data["longitude"] = data["origin_longitude"]
            elif data.get("longitude") is not None and data.get("origin_longitude") is None:
                data["origin_longitude"] = data["longitude"]

            if data.get("origin_name") and (not data.get("location_name") or data.get("location_name") == "Marine Operational Area"):
                data["location_name"] = data["origin_name"]
            elif data.get("location_name") and not data.get("origin_name"):
                data["origin_name"] = data["location_name"]

            # Validate presence of origin when query is not provided
            if data.get("latitude") is None and data.get("origin_latitude") is None and not query_text:
                raise ValueError("Origin latitude is required for marine analysis.")
            if data.get("longitude") is None and data.get("origin_longitude") is None and not query_text:
                raise ValueError("Origin longitude is required for marine analysis.")

            # 2. Check destination and identical endpoints
            dest_lat = data.get("destination_latitude")
            dest_lon = data.get("destination_longitude")
            lat = data.get("latitude")
            lon = data.get("longitude")
            waypoints = data.get("waypoints") or []

            if dest_lat is not None and dest_lon is not None and lat is not None and lon is not None:
                if float(dest_lat) == float(lat) and float(dest_lon) == float(lon) and not waypoints:
                    raise ValueError(
                        f"Route origin and destination coordinates are identical ({lat}, {lon}). "
                        "A valid marine route requires distinct origin and destination coordinates."
                    )

            # If passage planning is requested without destination coordinates, the orchestrator
            # node records status='insufficient_evidence' and appends to missing_evidence.
            return data


class OrchestratorAnalyzeResponse(BaseModel):
    """Response schema for ORCA Orchestrator Agent."""

    agent: str = "ORCA Orchestrator Agent"
    status: str  # "success", "partial_failure", "insufficient_evidence", "error", "clarification_needed"
    user_objective: str
    location: dict[str, Any]
    plan: dict[str, Any]
    summary: str
    descriptive_synthesis: str | None = None
    generation_mode: str = "deterministic"
    clarification_needed: bool = False
    clarification_prompt: str | None = None
    missing_inputs: list[str] = Field(default_factory=list)
    composite_safety_risk: dict[str, Any]
    measured_observations: dict[str, Any]
    derived_estimates: dict[str, Any]
    individual_agent_results: dict[str, Any]
    evidence_sources: list[dict[str, Any]] = Field(default_factory=list)
    timestamps: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    errors: dict[str, str] = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    legal_disclaimer: str
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


