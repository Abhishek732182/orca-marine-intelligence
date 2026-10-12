"""Specialist agent tool integrations for the AI Workspace Assistant.

Calls the existing independent specialist agents without replacing their logic
or modifying their contracts.
"""

from typing import Any

from app.agents.fishing_zone_agent import FishingZoneAgent
from app.agents.ocean_agent import OceanAgent
from app.agents.route_agent import RouteAgent
from app.agents.safety_risk_agent import SafetyRiskAgent
from app.agents.weather_agent import WeatherAgent
from app.data_sources.open_meteo_marine import OpenMeteoMarineProvider
from app.data_sources.open_meteo_weather import OpenMeteoWeatherProvider
from app.schemas.agent_schemas import (
    FishingZoneAnalyzeRequest,
    OceanAnalyzeRequest,
    RouteAnalyzeRequest,
    SafetyRiskAnalyzeRequest,
    WeatherAnalyzeRequest,
)

from app.data_sources.ingestion_worker import get_fisheries_worker

# Shared specialist agent instances for workspace assistant
_weather_agent = WeatherAgent()
_ocean_agent = OceanAgent()
_fishing_agent = FishingZoneAgent(fisheries_provider=get_fisheries_worker())
_route_agent = RouteAgent()
_safety_agent = SafetyRiskAgent()


async def tool_weather_agent(
    latitude: float,
    longitude: float,
    location_name: str | None = None,
    forecast_days: int = 1,
) -> dict[str, Any]:
    """Retrieve atmospheric weather telemetry and wind conditions."""
    req = WeatherAnalyzeRequest(
        latitude=latitude,
        longitude=longitude,
        location_name=location_name,
        forecast_days=max(1, min(7, forecast_days)),
    )
    res = await _weather_agent.analyze(req)
    return res.model_dump()


async def tool_ocean_agent(
    latitude: float,
    longitude: float,
    location_name: str = "Offshore Marine Location",
    forecast_time_window_hours: int = 24,
) -> dict[str, Any]:
    """Retrieve sea state and wave height telemetry using WMO Code Table 3700 standards."""
    req = OceanAnalyzeRequest(
        latitude=latitude,
        longitude=longitude,
        location_name=location_name,
        forecast_time_window_hours=max(1, min(168, forecast_time_window_hours)),
    )
    res = await _ocean_agent.analyze(req)
    return res.model_dump()


async def tool_fishing_zone_agent(
    latitude: float | None = None,
    longitude: float | None = None,
    location_name: str | None = None,
    forecast_time_window_hours: int = 24,
    target_species: str | None = None,
) -> dict[str, Any]:
    """Evaluate operational fisheries feasibility while disclosing biological telemetry limitations."""
    req = FishingZoneAnalyzeRequest(
        latitude=latitude,
        longitude=longitude,
        location_name=location_name,
        forecast_time_window_hours=forecast_time_window_hours,
        target_species=target_species,
    )
    res = await _fishing_agent.analyze(req)
    return res.model_dump()


async def tool_route_agent(
    origin_latitude: float | None = None,
    origin_longitude: float | None = None,
    destination_latitude: float | None = None,
    destination_longitude: float | None = None,
    origin_name: str | None = "Origin Point",
    destination_name: str | None = "Destination Point",
    vessel_speed_knots: float = 12.0,
    waypoints: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Calculate Great-Circle geodesic distance, initial bearings, and estimated transit duration."""
    if origin_latitude is None or origin_longitude is None:
        raise ValueError("Missing origin coordinates: origin_latitude and origin_longitude are required.")
    if destination_latitude is None or destination_longitude is None:
        raise ValueError("Missing destination coordinates: destination_latitude and destination_longitude are required.")
    req = RouteAnalyzeRequest(
        origin_latitude=origin_latitude,
        origin_longitude=origin_longitude,
        destination_latitude=destination_latitude,
        destination_longitude=destination_longitude,
        origin_name=origin_name,
        destination_name=destination_name,
        vessel_speed_knots=max(1.0, min(60.0, vessel_speed_knots)),
        waypoints=waypoints or [],
    )
    res = await _route_agent.analyze(req)
    return res.model_dump()


async def tool_safety_risk_agent(
    latitude: float,
    longitude: float,
    location_name: str | None = "Marine Position",
    vessel_type: str = "small_craft",
    wave_height_m: float | None = None,
    wind_speed_knots: float | None = None,
    precipitation_mm: float | None = None,
) -> dict[str, Any]:
    """Assess operational hazards, gale warnings, and vessel survival thresholds."""
    req = SafetyRiskAnalyzeRequest(
        latitude=latitude,
        longitude=longitude,
        location_name=location_name,
        vessel_type=vessel_type,
        wave_height_m=wave_height_m,
        wind_speed_knots=wind_speed_knots,
        precipitation_mm=precipitation_mm,
    )
    res = await _safety_agent.analyze(req)
    return res.model_dump()


async def tool_system_health() -> dict[str, Any]:
    """Check system operational status and provider connectivity."""
    marine_provider = OpenMeteoMarineProvider()
    weather_provider = OpenMeteoWeatherProvider()
    return {
        "service": "ORCA Marine Intelligence Assistant",
        "status": "healthy",
        "specialist_agents": [
            "Weather Agent (Open-Meteo Weather)",
            "Ocean Agent (Open-Meteo Marine)",
            "Fishing Zone Agent (Sea State & Fish Telemetry Grounding)",
            "Route Agent (Great-Circle Geodesic Math)",
            "Safety/Risk Agent (WMO 3700 & Beaufort Rule Engine)",
        ],
        "endpoints_available": {
            "weather": "/api/agents/weather/analyze",
            "ocean": "/api/agents/ocean/analyze",
            "fishing_zone": "/api/agents/fishing-zone/analyze",
            "route": "/api/agents/route/analyze",
            "safety_risk": "/api/agents/safety-risk/analyze",
            "orchestrator": "/api/agents/orchestrator/analyze",
            "assistant": "/api/agents/assistant/chat",
        },
    }
