"""Unit and API integration tests for ORCA Orchestrator Agent (Agent 6).

Covers:
- Successful orchestration across all specialist agents
- Objective-based planning (fishing, passage_planning, safety_check, general_maritime, all)
- Parallel specialist execution
- Partial specialist failures and error preservation
- Insufficient evidence preservation without data fabrication
- Safety/Risk preservation (CRITICAL/HIGH never downgraded; missing telemetry never LOW)
- Distinction between measured observations and geodesic/derived estimates
- Input validation (HTTP 422) on out-of-bounds coordinates
- Route handling when destination coordinates are missing
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.agents.orchestrator_agent import OrchestratorAgent, LEGAL_DISCLAIMER
from app.schemas.agent_schemas import (
    FishingZoneAnalyzeResponse,
    OceanAnalyzeResponse,
    OrchestratorAnalyzeRequest,
    OrchestratorAnalyzeResponse,
    RouteAnalyzeResponse,
    SafetyRiskAnalyzeResponse,
    WeatherAnalyzeResponse,
    WaypointItem,
)

client = TestClient(app)


def _make_dummy_weather(status="success", temp=28.0, wind_kts=16.0, wind_dir=240.0, precip=0.0):
    return WeatherAnalyzeResponse(
        agent="Weather Agent",
        status=status,
        location={"location_name": "Offshore Goa", "latitude": 15.0, "longitude": 72.0},
        data_source={"provider": "Open-Meteo Weather"},
        observations={
            "temperature_c": temp,
            "wind_speed_knots": wind_kts,
            "wind_direction_deg": wind_dir,
            "precipitation_mm": precip,
        },
        forecast=[],
        analysis={"wind_regime": "Moderate breeze"},
        warnings=[],
    )


def _make_dummy_ocean(status="success", wave_h=1.4, wmo_code=3, wmo_desc="Slight (0.5 - 1.25 m)"):
    return OceanAnalyzeResponse(
        agent="Ocean Agent",
        status=status,
        location={"location_name": "Offshore Goa", "latitude": 15.0, "longitude": 72.0},
        data_source={"provider": "Open-Meteo Marine"},
        observations={"wave_height_m": wave_h, "sample_count": 24},
        analysis={"wmo_sea_state": {"code": wmo_code, "description": wmo_desc}},
        warnings=[],
    )


def _make_dummy_fishing(status="success", suitability="FAVORABLE", feasibility="HIGH"):
    return FishingZoneAnalyzeResponse(
        agent="Fishing Zone Agent",
        status=status,
        location={"location_name": "Offshore Goa", "latitude": 15.0, "longitude": 72.0},
        data_source={"provider": "Open-Meteo Marine"},
        observations={"wave_height_m": 1.4},
        analysis={
            "zone_suitability": suitability,
            "operational_feasibility": feasibility,
            "fish_distribution_disclaimer": "Direct fish location telemetry is unavailable.",
        },
        warnings=[],
    )


def _make_dummy_route(status="success", dist_km=430.5, dist_nm=232.4, hours=19.4):
    return RouteAnalyzeResponse(
        agent="Route Agent",
        status=status,
        location={"origin": "Offshore Goa", "destination": "Mumbai Port"},
        data_source={"calculation_method": "Haversine Great-Circle geodesic formula"},
        observations={"total_distance_km": dist_km, "total_distance_nm": dist_nm, "waypoint_count": 2},
        analysis={"estimated_transit_hours": hours},
        warnings=["Straight-line geodesic distance only; does not reflect navigable marine channels."],
    )


def _make_dummy_safety(status="success", risk_category="MODERATE", risk_score=45, wave_h=1.4, wind_kts=16.0):
    return SafetyRiskAnalyzeResponse(
        agent="Safety/Risk Agent",
        status=status,
        location={"location_name": "Offshore Goa", "latitude": 15.0, "longitude": 72.0},
        data_source={"providers_attempted": ["Open-Meteo Marine", "Open-Meteo Weather"]},
        observations={"wave_height_m": wave_h, "wind_speed_knots": wind_kts, "precipitation_mm": 0.0},
        analysis={
            "risk_category": risk_category,
            "risk_score": risk_score,
            "risk_reasons": [f"Operational risk evaluated as {risk_category}."],
            "recommendations": ["Exercise caution and maintain VHF radio watch."],
        },
        warnings=[],
    )


# ==============================================================================
# Unit Tests for OrchestratorAgent
# ==============================================================================

@pytest.mark.asyncio
async def test_orchestrator_full_success_all_agents():
    """Verify orchestrator successfully plans, executes all 5 specialists in parallel, and synthesizes output."""
    mock_weather = AsyncMock()
    mock_weather.analyze.return_value = _make_dummy_weather()
    mock_ocean = AsyncMock()
    mock_ocean.analyze.return_value = _make_dummy_ocean()
    mock_fishing = AsyncMock()
    mock_fishing.analyze.return_value = _make_dummy_fishing()
    mock_route = AsyncMock()
    mock_route.analyze.return_value = _make_dummy_route()
    mock_safety = AsyncMock()
    mock_safety.analyze.return_value = _make_dummy_safety()

    orchestrator = OrchestratorAgent(
        weather_agent=mock_weather,
        ocean_agent=mock_ocean,
        fishing_zone_agent=mock_fishing,
        route_agent=mock_route,
        safety_risk_agent=mock_safety,
    )

    req = OrchestratorAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        location_name="Offshore Goa",
        user_objective="all",
        destination_latitude=18.9,
        destination_longitude=72.8,
        destination_name="Mumbai Port",
    )

    res = await orchestrator.analyze(req)

    assert isinstance(res, OrchestratorAnalyzeResponse)
    assert res.agent == "ORCA Orchestrator Agent"
    assert res.status == "success"
    assert res.user_objective == "all"

    # Verify all 5 agents were called
    assert mock_weather.analyze.await_count == 1
    assert mock_ocean.analyze.await_count == 1
    assert mock_fishing.analyze.await_count == 1
    assert mock_route.analyze.await_count == 1
    assert mock_safety.analyze.await_count == 1

    # Verify individual results captured
    assert "weather" in res.individual_agent_results
    assert "ocean" in res.individual_agent_results
    assert "fishing_zone" in res.individual_agent_results
    assert "route" in res.individual_agent_results
    assert "safety_risk" in res.individual_agent_results

    # Verify measured observations vs derived estimates separation
    assert res.measured_observations["wave_height_m"] == 1.4
    assert res.measured_observations["wind_speed_knots"] == 16.0
    assert res.measured_observations["temperature_c"] == 28.0
    assert res.derived_estimates["geodesic_route"]["distance_km"] == 430.5
    assert "NOT a verified" in res.derived_estimates["geodesic_route"]["navigability_disclaimer"]
    assert "UNVERIFIED" in res.derived_estimates["fisheries_suitability"]["biological_distribution_status"]

    # Verify safety risk
    assert res.composite_safety_risk["risk_category"] == "MODERATE"
    assert res.legal_disclaimer == LEGAL_DISCLAIMER

    # Verify WMO Code Table 3700 discrepancy warning is explicitly raised without altering provider data
    assert any("Observation discrepancy" in w for w in res.warnings)
    assert "wmo_discrepancy_warning" in res.measured_observations
    assert res.measured_observations["wmo_sea_state_code"] == 3


@pytest.mark.asyncio
async def test_orchestrator_objective_planning():
    """Verify objective-based pruning of specialists."""
    mock_weather = AsyncMock()
    mock_weather.analyze.return_value = _make_dummy_weather()
    mock_ocean = AsyncMock()
    mock_ocean.analyze.return_value = _make_dummy_ocean()
    mock_fishing = AsyncMock()
    mock_fishing.analyze.return_value = _make_dummy_fishing()
    mock_route = AsyncMock()
    mock_route.analyze.return_value = _make_dummy_route()
    mock_safety = AsyncMock()
    mock_safety.analyze.return_value = _make_dummy_safety()

    orchestrator = OrchestratorAgent(
        weather_agent=mock_weather,
        ocean_agent=mock_ocean,
        fishing_zone_agent=mock_fishing,
        route_agent=mock_route,
        safety_risk_agent=mock_safety,
    )

    # 1. Objective: safety_check (should only run weather, ocean, safety_risk)
    req_safety = OrchestratorAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        user_objective="safety_check",
    )
    res_safety = await orchestrator.analyze(req_safety)
    assert set(res_safety.plan["planned_agents"]) == {"weather", "ocean", "safety_risk"}
    assert mock_route.analyze.await_count == 0
    assert mock_fishing.analyze.await_count == 0

    # 2. Objective: passage_planning with destination
    req_route = OrchestratorAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        user_objective="passage_planning",
        destination_latitude=18.9,
        destination_longitude=72.8,
    )
    res_route = await orchestrator.analyze(req_route)
    assert set(res_route.plan["planned_agents"]) == {"weather", "ocean", "route", "safety_risk"}
    assert mock_route.analyze.await_count == 1
    assert mock_fishing.analyze.await_count == 0


@pytest.mark.asyncio
async def test_orchestrator_partial_failure_handling():
    """Verify orchestrator preserves successful agents when one specialist raises an error."""
    mock_weather = AsyncMock()
    mock_weather.analyze.side_effect = RuntimeError("Open-Meteo Weather API 503 Service Unavailable")
    mock_ocean = AsyncMock()
    mock_ocean.analyze.return_value = _make_dummy_ocean()
    mock_safety = AsyncMock()
    mock_safety.analyze.return_value = _make_dummy_safety()

    orchestrator = OrchestratorAgent(
        weather_agent=mock_weather,
        ocean_agent=mock_ocean,
        safety_risk_agent=mock_safety,
    )

    req = OrchestratorAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        user_objective="safety_check",
    )

    res = await orchestrator.analyze(req)

    # Status must be partial_failure, not success
    assert res.status == "partial_failure"
    assert "weather" in res.errors
    assert "503 Service Unavailable" in res.errors["weather"]

    # Ocean and safety results must be preserved
    assert res.individual_agent_results["weather"]["status"] == "error"
    assert res.individual_agent_results["ocean"]["status"] == "success"
    assert res.individual_agent_results["safety_risk"]["status"] == "success"
    assert res.measured_observations["wave_height_m"] == 1.4


@pytest.mark.asyncio
async def test_orchestrator_insufficient_evidence_preservation():
    """Verify insufficient evidence from specialists is preserved and never fabricated."""
    mock_weather = AsyncMock()
    mock_weather.analyze.return_value = _make_dummy_weather()
    mock_ocean = AsyncMock()
    mock_ocean.analyze.return_value = OceanAnalyzeResponse(
        agent="Ocean Agent",
        status="insufficient_evidence",
        location={"location_name": "Inland", "requested_latitude": 21.0, "requested_longitude": 79.0},
        data_source={"provider": "Open-Meteo Marine"},
        observations={"sample_count": 0, "timeseries": []},
        analysis={"summary": "Zero marine records retrieved for terrestrial position."},
        warnings=["Location appears to be on land."],
        error="Terrestrial coordinates outside ocean numerical grid.",
    )
    mock_safety = AsyncMock()
    mock_safety.analyze.return_value = SafetyRiskAnalyzeResponse(
        agent="Safety/Risk Agent",
        status="insufficient_evidence",
        location={"location_name": "Inland", "latitude": 21.0, "longitude": 79.0},
        data_source={"providers_attempted": ["Open-Meteo Marine"]},
        observations={"wave_height_m": None, "wind_speed_knots": None},
        analysis={
            "risk_category": "UNKNOWN / INSUFFICIENT EVIDENCE",
            "risk_score": None,
            "risk_reasons": ["No wave or wind telemetry could be retrieved."],
            "recommendations": ["DO NOT PRESUME SAFE: Absence of data does NOT imply safe navigation."],
        },
        warnings=["Missing marine observations; risk level cannot be verified."],
        error="No telemetry available",
    )

    orchestrator = OrchestratorAgent(
        weather_agent=mock_weather,
        ocean_agent=mock_ocean,
        safety_risk_agent=mock_safety,
    )

    req = OrchestratorAnalyzeRequest(
        latitude=21.0,
        longitude=79.0,
        location_name="Inland Position",
        user_objective="safety_check",
    )

    res = await orchestrator.analyze(req)

    assert res.status == "insufficient_evidence"
    assert res.composite_safety_risk["risk_category"] == "UNKNOWN / INSUFFICIENT EVIDENCE"
    assert res.composite_safety_risk["risk_score"] is None
    # Verify missing evidence is preserved
    assert any("Ocean" in item for item in res.missing_evidence)
    # Never claim safe or LOW
    assert res.composite_safety_risk["risk_category"] != "LOW"
    assert not any("Favorable" in r for r in res.recommendations)


@pytest.mark.asyncio
async def test_orchestrator_preserves_critical_safety():
    """Verify safety risk CRITICAL is strictly preserved and operations are halted."""
    mock_safety = AsyncMock()
    mock_safety.analyze.return_value = SafetyRiskAnalyzeResponse(
        agent="Safety/Risk Agent",
        status="success",
        location={"location_name": "Cyclone Zone", "latitude": 15.0, "longitude": 72.0},
        data_source={"providers_attempted": ["Open-Meteo Marine"]},
        observations={"wave_height_m": 5.2, "wind_speed_knots": 48.0},
        analysis={
            "risk_category": "CRITICAL",
            "risk_score": 95,
            "risk_reasons": ["Violent storm wave height: 5.2m exceeds vessel survival limit."],
            "recommendations": ["DANGER: Suspend all maritime operations immediately. Seek shelter."],
        },
        warnings=["Hazardous sea state: wave height >= 5.0m."],
    )

    orchestrator = OrchestratorAgent(
        weather_agent=AsyncMock(analyze=AsyncMock(return_value=_make_dummy_weather(wind_kts=48.0))),
        ocean_agent=AsyncMock(analyze=AsyncMock(return_value=_make_dummy_ocean(wave_h=5.2))),
        safety_risk_agent=mock_safety,
    )

    req = OrchestratorAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        user_objective="safety_check",
        vessel_type="small_craft",
    )

    res = await orchestrator.analyze(req)

    assert res.composite_safety_risk["risk_category"] == "CRITICAL"
    assert res.composite_safety_risk["risk_score"] == 95
    assert any("DANGER" in r or "Suspend" in r for r in res.recommendations)


@pytest.mark.asyncio
async def test_orchestrator_preserves_high_safety():
    """Verify safety risk HIGH is strictly preserved."""
    mock_safety = AsyncMock()
    mock_safety.analyze.return_value = SafetyRiskAnalyzeResponse(
        agent="Safety/Risk Agent",
        status="success",
        location={"location_name": "Rough Waters", "latitude": 15.0, "longitude": 72.0},
        data_source={"providers_attempted": ["Open-Meteo Marine"]},
        observations={"wave_height_m": 2.8, "wind_speed_knots": 25.0},
        analysis={
            "risk_category": "HIGH",
            "risk_score": 75,
            "risk_reasons": ["Wave height 2.8m exceeds small craft safe envelope."],
            "recommendations": ["HIGH RISK: Small craft stay ashore."],
        },
        warnings=[],
    )

    orchestrator = OrchestratorAgent(
        weather_agent=AsyncMock(analyze=AsyncMock(return_value=_make_dummy_weather())),
        ocean_agent=AsyncMock(analyze=AsyncMock(return_value=_make_dummy_ocean(wave_h=2.8))),
        safety_risk_agent=mock_safety,
    )

    req = OrchestratorAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        user_objective="safety_check",
        vessel_type="small_craft",
    )

    res = await orchestrator.analyze(req)
    assert res.composite_safety_risk["risk_category"] == "HIGH"


@pytest.mark.asyncio
async def test_orchestrator_passage_planning_without_destination():
    """Verify route planning without destination coordinates handles missing input gracefully."""
    orchestrator = OrchestratorAgent(
        weather_agent=AsyncMock(analyze=AsyncMock(return_value=_make_dummy_weather())),
        ocean_agent=AsyncMock(analyze=AsyncMock(return_value=_make_dummy_ocean())),
        safety_risk_agent=AsyncMock(analyze=AsyncMock(return_value=_make_dummy_safety())),
    )

    req = OrchestratorAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        user_objective="passage_planning",
        # destination_latitude and longitude omitted
    )

    res = await orchestrator.analyze(req)
    assert "route" in res.individual_agent_results
    assert res.individual_agent_results["route"]["status"] == "insufficient_evidence"
    assert any("destination" in item.lower() for item in res.missing_evidence)


# ==============================================================================
# API Endpoint Integration Tests (POST /api/agents/orchestrator/analyze)
# ==============================================================================

def test_orchestrator_api_endpoint_registered():
    """Verify orchestrator endpoint is registered in OpenAPI documentation."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/agents/orchestrator/analyze" in paths


def test_orchestrator_api_endpoint_success(monkeypatch):
    """Test POST /api/agents/orchestrator/analyze with valid payload."""
    from app.api.routes.agents import orchestrator

    mock_w = AsyncMock(return_value=_make_dummy_weather())
    mock_o = AsyncMock(return_value=_make_dummy_ocean())
    mock_fz = AsyncMock(return_value=_make_dummy_fishing())
    mock_sr = AsyncMock(return_value=_make_dummy_safety())

    monkeypatch.setattr(orchestrator.agent.weather_agent, "analyze", mock_w)
    monkeypatch.setattr(orchestrator.agent.ocean_agent, "analyze", mock_o)
    monkeypatch.setattr(orchestrator.agent.fishing_zone_agent, "analyze", mock_fz)
    monkeypatch.setattr(orchestrator.agent.safety_risk_agent, "analyze", mock_sr)

    res = client.post(
        "/api/agents/orchestrator/analyze",
        json={
            "latitude": 15.0,
            "longitude": 72.0,
            "location_name": "Offshore Goa",
            "user_objective": "fishing",
            "vessel_type": "small_craft",
            "target_species": "Mackerel",
        },
    )

    assert res.status_code == 200
    data = res.json()
    assert data["agent"] == "ORCA Orchestrator Agent"
    assert data["status"] == "success"
    assert data["user_objective"] == "fishing"
    assert "weather" in data["individual_agent_results"]
    assert "ocean" in data["individual_agent_results"]
    assert "fishing_zone" in data["individual_agent_results"]
    assert "safety_risk" in data["individual_agent_results"]
    assert data["composite_safety_risk"]["risk_category"] == "MODERATE"


def test_orchestrator_api_endpoint_rejects_out_of_bounds_coordinates():
    """Verify endpoint rejects invalid coordinates with HTTP 422."""
    res = client.post(
        "/api/agents/orchestrator/analyze",
        json={
            "latitude": 95.0,  # Invalid latitude (> 90)
            "longitude": 72.0,
        },
    )
    assert res.status_code == 422
    errors = res.json().get("detail", [])
    assert any("latitude" in str(err) for err in errors)


def test_orchestrator_api_endpoint_preserves_critical_hazard(monkeypatch):
    """Verify endpoint strictly preserves CRITICAL safety risk."""
    from app.api.routes.agents import orchestrator

    critical_safety = _make_dummy_safety(risk_category="CRITICAL", risk_score=95)
    critical_safety.analysis["recommendations"] = [
        "DANGER: Severe gale wave heights exceed vessel survivability. Suspend all operations."
    ]

    monkeypatch.setattr(orchestrator.agent.weather_agent, "analyze", AsyncMock(return_value=_make_dummy_weather()))
    monkeypatch.setattr(orchestrator.agent.ocean_agent, "analyze", AsyncMock(return_value=_make_dummy_ocean(wave_h=4.5)))
    monkeypatch.setattr(orchestrator.agent.safety_risk_agent, "analyze", AsyncMock(return_value=critical_safety))

    res = client.post(
        "/api/agents/orchestrator/analyze",
        json={
            "latitude": 15.0,
            "longitude": 72.0,
            "user_objective": "safety_check",
            "vessel_type": "small_craft",
        },
    )

    assert res.status_code == 200
    data = res.json()
    assert data["composite_safety_risk"]["risk_category"] == "CRITICAL"
    assert any("DANGER" in r for r in data["recommendations"])


# ==============================================================================
# Regression Tests for Agent 6 Integration & Verification
# ==============================================================================

@pytest.mark.asyncio
async def test_orchestrator_execution_reporting_planned_attempted_executed_failed_skipped():
    """Verify Agent 6 accurately reports planned, attempted, executed, failed, and skipped agents."""
    mock_weather = AsyncMock()
    mock_weather.analyze.side_effect = RuntimeError("Weather service connection timeout")
    mock_ocean = AsyncMock()
    mock_ocean.analyze.return_value = _make_dummy_ocean()
    mock_fishing = AsyncMock()
    mock_fishing.analyze.return_value = _make_dummy_fishing()
    mock_safety = AsyncMock()
    mock_safety.analyze.return_value = _make_dummy_safety()

    orchestrator = OrchestratorAgent(
        weather_agent=mock_weather,
        ocean_agent=mock_ocean,
        fishing_zone_agent=mock_fishing,
        safety_risk_agent=mock_safety,
    )

    # Request with user_objective="all", but omitting destination coordinates so route is skipped
    req = OrchestratorAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        user_objective="all",
        # destination omitted
    )

    res = await orchestrator.analyze(req)

    plan = res.plan
    assert set(plan["planned_agents"]) == {"weather", "ocean", "fishing_zone", "route", "safety_risk"}
    # Attempted: dispatched tasks
    assert set(plan["attempted_agents"]) == {"weather", "ocean", "fishing_zone", "safety_risk"}
    # Skipped: route had no destination
    assert plan["skipped_agents"] == ["route"]
    # Failed: weather raised RuntimeError
    assert plan["failed_agents"] == ["weather"]
    # Executed: successfully executed agents (NOT failed, NOT skipped)
    assert set(plan["executed_agents"]) == {"ocean", "fishing_zone", "safety_risk"}
    # Critical invariant: Neither failed nor skipped agents are marked as executed
    assert "weather" not in plan["executed_agents"]
    assert "route" not in plan["executed_agents"]


@pytest.mark.asyncio
async def test_orchestrator_ocean_real_schema_mapping_no_na():
    """Verify orchestrator maps real OceanAgent schema without producing N/A for valid wave data."""
    # Build OceanAnalyzeResponse exactly as OceanAgent produces it
    real_ocean_response = OceanAnalyzeResponse(
        agent="Ocean Agent",
        status="success",
        location={"location_name": "Offshore Goa", "requested_latitude": 15.0, "requested_longitude": 72.0},
        data_source={"provider": "Open-Meteo Marine Weather API"},
        observations={
            "sample_count": 24,
            "wave_height_m": 1.85,
            "min_wave_height_m": 0.90,
            "max_wave_height_m": 1.85,
            "avg_wave_height_m": 1.35,
            "latest_wave_height_m": 1.20,
            "timeseries": [],
            "units": {"wave_height": "m"},
        },
        analysis={
            "sea_state_code": 4,
            "sea_state_category": "Moderate",
            "description": "1.25 to 2.5 m",
            "wmo_sea_state": {
                "code": 4,
                "category": "Moderate",
                "description": "1.25 to 2.5 m",
            },
            "rule_standard": "WMO Code Table 3700",
            "summary": "Wave heights reach 1.85 m (Moderate, WMO Code 4).",
        },
        warnings=[],
    )

    mock_ocean = AsyncMock()
    mock_ocean.analyze.return_value = real_ocean_response

    orchestrator = OrchestratorAgent(
        weather_agent=AsyncMock(analyze=AsyncMock(return_value=_make_dummy_weather())),
        ocean_agent=mock_ocean,
        safety_risk_agent=AsyncMock(analyze=AsyncMock(return_value=_make_dummy_safety())),
    )

    req = OrchestratorAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        user_objective="safety_check",
    )

    res = await orchestrator.analyze(req)

    # Wave height and sea state must NOT be None or N/A
    assert res.measured_observations["wave_height_m"] == 1.85
    assert res.measured_observations["wmo_sea_state_code"] == 4
    assert res.measured_observations["wmo_sea_state_description"] == "1.25 to 2.5 m"
    assert "1.85" in res.summary


@pytest.mark.asyncio
async def test_orchestrator_ocean_missing_evidence_preserves_none():
    """Verify orchestrator preserves missing telemetry as None/unverified when OceanAgent reports insufficient evidence."""
    missing_ocean = OceanAnalyzeResponse(
        agent="Ocean Agent",
        status="insufficient_evidence",
        location={"location_name": "Inland", "requested_latitude": 20.0, "requested_longitude": 78.0},
        data_source={"provider": "Open-Meteo Marine"},
        observations={"sample_count": 0, "wave_height_m": None, "timeseries": []},
        analysis={
            "sea_state_code": None,
            "sea_state_category": "UNKNOWN",
            "wmo_sea_state": None,
            "summary": "All returned wave-height values were null.",
        },
        warnings=["All retrieved wave heights null."],
    )

    orchestrator = OrchestratorAgent(
        weather_agent=AsyncMock(analyze=AsyncMock(return_value=_make_dummy_weather())),
        ocean_agent=AsyncMock(analyze=AsyncMock(return_value=missing_ocean)),
        safety_risk_agent=AsyncMock(analyze=AsyncMock(return_value=_make_dummy_safety(risk_category="UNKNOWN / INSUFFICIENT EVIDENCE", risk_score=None, wave_h=None))),
    )

    req = OrchestratorAnalyzeRequest(
        latitude=20.0,
        longitude=78.0,
        user_objective="safety_check",
    )

    res = await orchestrator.analyze(req)

    # Measured observations must preserve None when telemetry is missing
    assert res.measured_observations["wave_height_m"] is None
    assert res.measured_observations["wmo_sea_state_code"] is None
    # Safety risk must NOT be LOW
    assert res.composite_safety_risk["risk_category"] != "LOW"


@pytest.mark.asyncio
async def test_safety_risk_hypothetical_severe_conditions_never_downgraded():
    """Verify Safety/Risk agent evaluates hypothetical 55 knot wind and 7m wave separately as CRITICAL, never downgraded."""
    from app.agents.safety_risk_agent import SafetyRiskAgent
    from app.schemas.agent_schemas import SafetyRiskAnalyzeRequest

    safety_agent = SafetyRiskAgent()

    # 1. Severe wind alone (55 knots with benign 1.0m wave)
    req_severe_wind = SafetyRiskAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        wave_height_m=1.0,
        wind_speed_knots=55.0,
        vessel_type="small_craft",
    )
    res_wind = await safety_agent.analyze(req_severe_wind)
    assert res_wind.analysis["risk_category"] == "CRITICAL"
    assert res_wind.analysis["risk_score"] >= 90
    assert any("Gale force winds" in r or "55.0 knots" in r for r in res_wind.analysis["risk_reasons"])
    assert res_wind.analysis["risk_category"] != "LOW"

    # 2. Severe wave alone (7.0 metres with calm 8.0 knot wind)
    req_severe_wave = SafetyRiskAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        wave_height_m=7.0,
        wind_speed_knots=8.0,
        vessel_type="small_craft",
    )
    res_wave = await safety_agent.analyze(req_severe_wave)
    assert res_wave.analysis["risk_category"] == "CRITICAL"
    assert res_wave.analysis["risk_score"] >= 90
    assert any("7.00 m" in r or "Critical" in r for r in res_wave.analysis["risk_reasons"])
    assert res_wave.analysis["risk_category"] != "LOW"

    # 3. Severe wave for commercial vessel (7.0 metres >= 6.0m commercial threshold)
    req_commercial_wave = SafetyRiskAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        wave_height_m=7.0,
        wind_speed_knots=8.0,
        vessel_type="commercial_cargo",
    )
    res_comm = await safety_agent.analyze(req_commercial_wave)
    assert res_comm.analysis["risk_category"] == "CRITICAL"
    assert res_comm.analysis["risk_score"] >= 90
    assert res_comm.analysis["risk_category"] != "LOW"

    # 4. Both severe (55 knots and 7.0m wave)
    req_both = SafetyRiskAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        wave_height_m=7.0,
        wind_speed_knots=55.0,
        vessel_type="small_craft",
    )
    res_both = await safety_agent.analyze(req_both)
    assert res_both.analysis["risk_category"] == "CRITICAL"
    assert res_both.analysis["risk_score"] >= 90


@pytest.mark.asyncio
async def test_fishing_zone_biological_distribution_remains_unverified():
    """Verify fishing zone biological fish distribution is strictly unverified rather than fabricated."""
    from app.agents.fishing_zone_agent import FishingZoneAgent
    from app.schemas.agent_schemas import FishingZoneAnalyzeRequest

    fz_agent = FishingZoneAgent()
    req = FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0, forecast_time_window_hours=24)
    res = await fz_agent.analyze(req)

    # Biological fish distribution must be explicitly UNVERIFIED
    verified_fish = res.analysis.get("verified_fish_distribution", {})
    assert verified_fish.get("status") == "UNVERIFIED"
    assert verified_fish.get("biomass_data_available") is False
    assert verified_fish.get("catch_probability") is None
    assert "No verified fish distribution" in verified_fish.get("statement", "")
    assert any("Direct pelagic fish biomass" in w or "unverified" in w.lower() for w in res.warnings)


@pytest.mark.asyncio
async def test_route_agent_geodesic_distinction_and_navigation_warnings():
    """Verify Route Agent distinguishes geodesic distance from an authorized channel and preserves warnings."""
    from app.agents.route_agent import RouteAgent
    from app.schemas.agent_schemas import RouteAnalyzeRequest

    route_agent = RouteAgent()
    req = RouteAnalyzeRequest(
        origin_latitude=15.0,
        origin_longitude=72.0,
        destination_latitude=18.9,
        destination_longitude=72.8,
        origin_name="Goa Sector",
        destination_name="Mumbai Port",
    )
    res = await route_agent.analyze(req)

    assert res.status == "success"
    assert res.observations["total_distance_km"] > 0
    assert res.observations["total_distance_nm"] > 0
    # Navigation warnings must be explicitly preserved
    assert any("geodesic straight-line distance" in w for w in res.warnings)
    assert any("DOES NOT replace Electronic Navigational Charts" in w for w in res.warnings)


@pytest.mark.asyncio
async def test_orchestrator_derived_estimates_geodesic_labeling_and_disclaimer():
    """Verify orchestrator labels route as estimated geodesic distance and includes critical disclaimer."""
    orchestrator = OrchestratorAgent()
    req = OrchestratorAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        destination_latitude=18.9,
        destination_longitude=72.8,
        user_objective="passage_planning",
    )
    res = await orchestrator.analyze(req)

    assert res.status == "success"
    geodesic_info = res.derived_estimates["geodesic_route"]
    assert geodesic_info["route_classification"] == "GEODESIC_STRAIGHT_LINE_ESTIMATE"
    assert geodesic_info["is_verified_navigable_route"] is False
    assert geodesic_info["distance_km"] > 0
    assert "CRITICAL NOTICE" in geodesic_info["navigability_disclaimer"]
    assert "Does NOT account for shallow bathymetry, shoals, reef hazards" in geodesic_info["navigability_disclaimer"]

    # Passage planning recommendation must state geodesic straight line
    assert any("Route is an estimated Great-Circle geodesic distance only" in r for r in res.recommendations)


@pytest.mark.asyncio
async def test_orchestrator_fisheries_separation_and_insufficient_evidence():
    """Verify orchestrator separates physical wave conditions from biological fisheries evidence and retains INSUFFICIENT_EVIDENCE."""
    orchestrator = OrchestratorAgent()
    req = OrchestratorAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        user_objective="fishing",
    )
    res = await orchestrator.analyze(req)

    fisheries_info = res.derived_estimates["fisheries_suitability"]
    assert fisheries_info["operational_feasibility_scope"] == "STRICTLY_PHYSICAL_WAVE_CONDITIONS"
    assert fisheries_info["zone_suitability"] == "INSUFFICIENT_EVIDENCE"
    assert "UNVERIFIED" in fisheries_info["biological_distribution_status"]

    # Legal disclaimer must cover both route tracks and fish distributions
    assert "Straight-line route distances do not constitute authorized hydrographic navigation tracks" in res.legal_disclaimer
    assert "Direct fish school distributions are unverified" in res.legal_disclaimer


@pytest.mark.asyncio
async def test_orchestrator_goa_to_mumbai_preserves_distinct_endpoints():
    """Bug 1 Regression: Verify Goa to Mumbai passage planning preserves distinct origin and destination throughout."""
    orchestrator = OrchestratorAgent()
    req = OrchestratorAnalyzeRequest(
        origin_latitude=15.0,
        origin_longitude=72.0,
        origin_name="Goa Sector",
        destination_latitude=18.95,
        destination_longitude=72.82,
        destination_name="Mumbai Port",
        user_objective="passage_planning",
        vessel_speed_knots=12.0,
    )
    res = await orchestrator.analyze(req)

    assert res.status == "success"
    # Ensure mission locations retain separate origin and destination
    assert res.location["origin"]["name"] == "Goa Sector"
    assert res.location["origin"]["latitude"] == 15.0
    assert res.location["origin"]["longitude"] == 72.0
    assert res.location["destination"]["name"] == "Mumbai Port"
    assert res.location["destination"]["latitude"] == 18.95
    assert res.location["destination"]["longitude"] == 72.82

    # Geodesic route in derived estimates must have distinct endpoints and correct distance
    route_est = res.derived_estimates["geodesic_route"]
    assert route_est["origin_latitude"] == 15.0
    assert route_est["origin_longitude"] == 72.0
    assert route_est["destination_latitude"] == 18.95
    assert route_est["destination_longitude"] == 72.82
    assert route_est["origin_name"] == "Goa Sector"
    assert route_est["destination_name"] == "Mumbai Port"
    assert 430.0 < route_est["distance_km"] < 460.0
    assert route_est["estimated_transit_hours"] > 15.0


def test_orchestrator_rejects_missing_origin():
    """Bug 1 Regression: Missing origin coordinates must raise explicit validation error."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc:
        OrchestratorAnalyzeRequest(
            origin_latitude=None,
            latitude=None,
            longitude=72.0,
            destination_latitude=18.95,
            destination_longitude=72.82,
        )
    assert "Origin latitude is required" in str(exc.value)


def test_orchestrator_rejects_identical_origin_destination():
    """Bug 1 Regression: Identical origin and destination coordinates must be rejected."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc:
        OrchestratorAnalyzeRequest(
            origin_latitude=18.95,
            origin_longitude=72.82,
            destination_latitude=18.95,
            destination_longitude=72.82,
            user_objective="passage_planning",
        )
    assert "identical" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_orchestrator_coordinate_propagation_to_route_specialist():
    """Bug 1 Regression: Verify actual origin and destination are passed to Route Agent without overwrite."""
    mock_route = AsyncMock(analyze=AsyncMock(return_value=_make_dummy_route(dist_km=446.2, dist_nm=241.0, hours=37.2)))
    orchestrator = OrchestratorAgent(
        weather_agent=AsyncMock(analyze=AsyncMock(return_value=_make_dummy_weather())),
        ocean_agent=AsyncMock(analyze=AsyncMock(return_value=_make_dummy_ocean())),
        safety_risk_agent=AsyncMock(analyze=AsyncMock(return_value=_make_dummy_safety())),
        route_agent=mock_route,
    )
    req = OrchestratorAnalyzeRequest(
        origin_latitude=15.0,
        origin_longitude=72.0,
        origin_name="Goa Sector",
        destination_latitude=18.95,
        destination_longitude=72.82,
        destination_name="Mumbai Port",
        user_objective="passage_planning",
    )
    await orchestrator.analyze(req)

    # Inspect call args to Route Agent
    mock_route.analyze.assert_called_once()
    route_req = mock_route.analyze.call_args[0][0]
    assert route_req.origin_latitude == 15.0
    assert route_req.origin_longitude == 72.0
    assert route_req.destination_latitude == 18.95
    assert route_req.destination_longitude == 72.82


