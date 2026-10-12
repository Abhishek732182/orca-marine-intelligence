"""End-to-End Integration Tests for ORCA Marine Intelligence & Fishing Advisory Platform.

Validates the full request flow through POST /api/agents/orchestrator/analyze and all 5 specialist agents:
1. Successful execution of all five specialist agents.
2. Partial agent failure and unavailable data providers.
3. Missing or stale evidence (INSUFFICIENT_EVIDENCE without data invention).
4. Conflicting specialist results (WMO code vs wave height discrepancy).
5. Critical and unknown safety conditions (never downgraded or treated as safe).
6. Geodesic route disclaimer (never presented as certified navigation track).
7. Consistent response fields between API and frontend contract.
"""

from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.api.routes.agents import orchestrator
from app.agents.orchestrator_agent import OrchestratorAgent, LEGAL_DISCLAIMER
from app.schemas.agent_schemas import (
    FishingZoneAnalyzeResponse,
    OceanAnalyzeResponse,
    RouteAnalyzeResponse,
    SafetyRiskAnalyzeResponse,
    WeatherAnalyzeResponse,
)

client = TestClient(app)


def _make_dummy_weather(temp=28.0, wind_kts=16.0, wind_dir=240.0, precip=0.0):
    return WeatherAnalyzeResponse(
        agent="Weather Agent",
        status="success",
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


def _make_dummy_ocean(wave_h=1.4, wmo_code=4, wmo_desc="Moderate (1.25 - 2.5 m)"):
    return OceanAnalyzeResponse(
        agent="Ocean Agent",
        status="success",
        location={"location_name": "Offshore Goa", "latitude": 15.0, "longitude": 72.0},
        data_source={"provider": "Open-Meteo Marine"},
        observations={"wave_height_m": wave_h, "sample_count": 24},
        analysis={
            "sea_state_code": wmo_code,
            "sea_state_category": "Moderate",
            "wmo_sea_state": {"code": wmo_code, "category": "Moderate", "description": wmo_desc},
        },
        warnings=[],
    )


def _make_dummy_fishing():
    return FishingZoneAnalyzeResponse(
        agent="Fishing Zone Agent",
        status="insufficient_evidence",
        location={"location_name": "Offshore Goa", "latitude": 15.0, "longitude": 72.0},
        data_source={"provider": "Open-Meteo Marine"},
        observations={"wave_height_m": 1.4},
        analysis={
            "zone_suitability": "INSUFFICIENT_EVIDENCE",
            "operational_feasibility": "FAVORABLE",
            "verified_fish_distribution": {
                "status": "UNVERIFIED",
                "biomass_data_available": False,
                "catch_probability": None,
                "statement": "Direct fish location telemetry is unavailable from numerical models.",
            },
        },
        warnings=["Direct pelagic fish biomass is unverified."],
    )


def _make_dummy_route(dist_km=430.5, dist_nm=232.4, hours=19.4):
    return RouteAnalyzeResponse(
        agent="Route Agent",
        status="success",
        location={"origin": "Offshore Goa", "destination": "Mumbai Port"},
        data_source={"calculation_method": "Haversine Great-Circle geodesic formula"},
        observations={"total_distance_km": dist_km, "total_distance_nm": dist_nm, "waypoint_count": 2},
        analysis={"estimated_transit_hours": hours},
        warnings=["Straight-line geodesic distance only; does not reflect navigable marine channels."],
    )


def _make_dummy_safety(risk_category="MODERATE", risk_score=45):
    return SafetyRiskAnalyzeResponse(
        agent="Safety/Risk Agent",
        status="success",
        location={"location_name": "Offshore Goa", "latitude": 15.0, "longitude": 72.0},
        data_source={"providers_attempted": ["Open-Meteo Marine", "Open-Meteo Weather"]},
        observations={"wave_height_m": 1.4, "wind_speed_knots": 16.0, "precipitation_mm": 0.0},
        analysis={
            "risk_category": risk_category,
            "risk_score": risk_score,
            "risk_reasons": [f"Operational risk evaluated as {risk_category}."],
            "recommendations": ["Exercise caution and maintain VHF radio watch."],
        },
        warnings=[],
    )


def test_e2e_all_five_specialists_execution(monkeypatch):
    """Test 1: Successful execution of all five specialist agents through orchestrator."""
    monkeypatch.setattr(orchestrator.agent.weather_agent, "analyze", AsyncMock(return_value=_make_dummy_weather()))
    monkeypatch.setattr(orchestrator.agent.ocean_agent, "analyze", AsyncMock(return_value=_make_dummy_ocean()))
    monkeypatch.setattr(orchestrator.agent.fishing_zone_agent, "analyze", AsyncMock(return_value=_make_dummy_fishing()))
    monkeypatch.setattr(orchestrator.agent.route_agent, "analyze", AsyncMock(return_value=_make_dummy_route()))
    monkeypatch.setattr(orchestrator.agent.safety_risk_agent, "analyze", AsyncMock(return_value=_make_dummy_safety()))

    res = client.post(
        "/api/agents/orchestrator/analyze",
        json={
            "origin_latitude": 15.0,
            "origin_longitude": 72.0,
            "origin_name": "Goa Offshore",
            "destination_latitude": 18.9,
            "destination_longitude": 72.8,
            "destination_name": "Mumbai Port",
            "user_objective": "all",
            "vessel_type": "small_craft",
            "target_species": "Mackerel",
        },
    )

    assert res.status_code == 200
    data = res.json()

    assert data["agent"] == "ORCA Orchestrator Agent"
    assert data["status"] == "success"
    assert data["user_objective"] == "all"

    # All five specialists must be planned, attempted, and executed
    assert set(data["plan"]["planned_agents"]) == {"weather", "ocean", "fishing_zone", "route", "safety_risk"}
    assert set(data["plan"]["executed_agents"]) == {"weather", "ocean", "fishing_zone", "route", "safety_risk"}
    assert data["plan"]["failed_agents"] == []
    assert data["plan"]["skipped_agents"] == []

    # Specialist results must all be present
    for key in ["weather", "ocean", "fishing_zone", "route", "safety_risk"]:
        assert key in data["individual_agent_results"]


def test_e2e_partial_failure_and_unavailable_provider(monkeypatch):
    """Test 2: Partial agent failure gracefully handles provider downtime without crashing."""
    # Weather agent experiences an upstream API 503 error
    monkeypatch.setattr(
        orchestrator.agent.weather_agent,
        "analyze",
        AsyncMock(side_effect=RuntimeError("Open-Meteo Weather 503 Service Unavailable")),
    )
    monkeypatch.setattr(orchestrator.agent.ocean_agent, "analyze", AsyncMock(return_value=_make_dummy_ocean()))
    monkeypatch.setattr(orchestrator.agent.safety_risk_agent, "analyze", AsyncMock(return_value=_make_dummy_safety()))

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

    assert data["status"] == "partial_failure"
    assert "weather" in data["plan"]["failed_agents"]
    assert "weather" in data["errors"]
    assert "503 Service Unavailable" in data["errors"]["weather"]

    # Ocean and safety risk must be preserved
    assert "ocean" in data["plan"]["executed_agents"]
    assert "safety_risk" in data["plan"]["executed_agents"]
    assert data["individual_agent_results"]["ocean"]["status"] == "success"
    assert data["individual_agent_results"]["safety_risk"]["status"] == "success"


def test_e2e_missing_or_stale_evidence_inland_preservation(monkeypatch):
    """Test 3: Missing or terrestrial evidence returns INSUFFICIENT_EVIDENCE and never fabricates data."""
    inland_ocean = OceanAnalyzeResponse(
        agent="Ocean Agent",
        status="insufficient_evidence",
        location={"location_name": "Inland Nagpur", "latitude": 21.15, "longitude": 79.09},
        data_source={"provider": "Open-Meteo Marine"},
        observations={"sample_count": 0, "wave_height_m": None},
        analysis={"summary": "Zero marine records for terrestrial coordinates."},
        warnings=["Terrestrial coordinates outside ocean numerical grid."],
        error="No marine data on land",
    )
    inland_safety = SafetyRiskAnalyzeResponse(
        agent="Safety/Risk Agent",
        status="insufficient_evidence",
        location={"location_name": "Inland Nagpur", "latitude": 21.15, "longitude": 79.09},
        data_source={"providers_attempted": ["Open-Meteo Marine"]},
        observations={"wave_height_m": None, "wind_speed_knots": None},
        analysis={
            "risk_category": "UNKNOWN / INSUFFICIENT EVIDENCE",
            "risk_score": None,
            "risk_reasons": ["Missing telemetry; absence of observations is NOT safe."],
            "recommendations": ["EVIDENCE INCOMPLETE: Do NOT presume calm conditions."],
        },
        warnings=["Missing marine telemetry."],
    )

    monkeypatch.setattr(orchestrator.agent.weather_agent, "analyze", AsyncMock(return_value=_make_dummy_weather()))
    monkeypatch.setattr(orchestrator.agent.ocean_agent, "analyze", AsyncMock(return_value=inland_ocean))
    monkeypatch.setattr(orchestrator.agent.safety_risk_agent, "analyze", AsyncMock(return_value=inland_safety))

    res = client.post(
        "/api/agents/orchestrator/analyze",
        json={
            "latitude": 21.15,
            "longitude": 79.09,
            "location_name": "Inland Nagpur",
            "user_objective": "safety_check",
        },
    )

    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "insufficient_evidence"
    assert data["measured_observations"]["wave_height_m"] is None
    assert data["composite_safety_risk"]["risk_category"] == "UNKNOWN / INSUFFICIENT EVIDENCE"
    assert data["composite_safety_risk"]["risk_score"] is None
    assert not any("Favorable" in r for r in data["recommendations"])
    assert any("EVIDENCE INCOMPLETE" in r for r in data["recommendations"])


def test_e2e_conflicting_specialist_results_detection(monkeypatch):
    """Test 4: Discrepancy between measured wave height and reported WMO code is detected and preserved."""
    # Wave height 1.85m is WMO Code 4 (Moderate, 1.25m - 2.5m).
    # Provide a conflicting reported code (Code 1 - Calm) to test conflict detection.
    conflicting_ocean = OceanAnalyzeResponse(
        agent="Ocean Agent",
        status="success",
        location={"location_name": "Offshore Goa", "latitude": 15.0, "longitude": 72.0},
        data_source={"provider": "Open-Meteo Marine"},
        observations={"wave_height_m": 1.85, "sample_count": 24},
        analysis={
            "sea_state_code": 1,  # Contradicts 1.85m wave height!
            "sea_state_category": "Calm (rippled)",
            "wmo_sea_state": {"code": 1, "category": "Calm (rippled)", "description": "Ripples"},
        },
        warnings=[],
    )

    monkeypatch.setattr(orchestrator.agent.weather_agent, "analyze", AsyncMock(return_value=_make_dummy_weather()))
    monkeypatch.setattr(orchestrator.agent.ocean_agent, "analyze", AsyncMock(return_value=conflicting_ocean))
    monkeypatch.setattr(orchestrator.agent.safety_risk_agent, "analyze", AsyncMock(return_value=_make_dummy_safety()))

    res = client.post(
        "/api/agents/orchestrator/analyze",
        json={
            "latitude": 15.0,
            "longitude": 72.0,
            "user_objective": "safety_check",
        },
    )

    assert res.status_code == 200
    data = res.json()

    # The discrepancy warning must be generated without destroying the provider's original data
    assert any("Observation discrepancy" in w for w in data["warnings"])
    assert "wmo_discrepancy_warning" in data["measured_observations"]
    # Preserves actual provider observation and reported code
    assert data["measured_observations"]["wave_height_m"] == 1.85
    assert data["measured_observations"]["wmo_sea_state_code"] == 1


def test_e2e_critical_safety_never_downgraded(monkeypatch):
    """Test 5a: Critical hazard conditions are strictly preserved and never downgraded."""
    severe_safety = SafetyRiskAnalyzeResponse(
        agent="Safety/Risk Agent",
        status="success",
        location={"location_name": "Severe Storm Sector", "latitude": 15.0, "longitude": 72.0},
        data_source={"providers_attempted": ["Open-Meteo Marine"]},
        observations={"wave_height_m": 5.8, "wind_speed_knots": 48.0},
        analysis={
            "risk_category": "CRITICAL",
            "risk_score": 96,
            "risk_reasons": ["Severe storm wave height: 5.8m and wind 48.0 knots exceeds vessel survivability."],
            "recommendations": ["DANGER: Suspend all operations immediately. Seek harbor protection."],
        },
        warnings=["Hazardous sea state: wave height >= 5.0m."],
    )

    monkeypatch.setattr(orchestrator.agent.weather_agent, "analyze", AsyncMock(return_value=_make_dummy_weather(wind_kts=48.0)))
    monkeypatch.setattr(orchestrator.agent.ocean_agent, "analyze", AsyncMock(return_value=_make_dummy_ocean(wave_h=5.8)))
    monkeypatch.setattr(orchestrator.agent.safety_risk_agent, "analyze", AsyncMock(return_value=severe_safety))

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
    assert data["composite_safety_risk"]["risk_score"] == 96
    assert any("DANGER" in r or "Suspend" in r for r in data["recommendations"])


def test_e2e_route_not_certified_navigation_passage(monkeypatch):
    """Test 6: Geodesic route is explicitly disclaimed and never presented as certified navigation passage."""
    monkeypatch.setattr(orchestrator.agent.weather_agent, "analyze", AsyncMock(return_value=_make_dummy_weather()))
    monkeypatch.setattr(orchestrator.agent.ocean_agent, "analyze", AsyncMock(return_value=_make_dummy_ocean()))
    monkeypatch.setattr(orchestrator.agent.route_agent, "analyze", AsyncMock(return_value=_make_dummy_route(dist_km=442.8)))
    monkeypatch.setattr(orchestrator.agent.safety_risk_agent, "analyze", AsyncMock(return_value=_make_dummy_safety()))

    res = client.post(
        "/api/agents/orchestrator/analyze",
        json={
            "origin_latitude": 15.0,
            "origin_longitude": 72.0,
            "origin_name": "Goa Mormugao",
            "destination_latitude": 18.9,
            "destination_longitude": 72.8,
            "destination_name": "Mumbai Port",
            "user_objective": "passage_planning",
            "vessel_type": "commercial_cargo",
        },
    )

    assert res.status_code == 200
    data = res.json()

    route_info = data["derived_estimates"]["geodesic_route"]
    assert route_info["is_verified_navigable_route"] is False
    assert route_info["route_classification"] == "GEODESIC_STRAIGHT_LINE_ESTIMATE"
    assert "CRITICAL NOTICE" in route_info["navigability_disclaimer"]
    assert "NOT a verified, safe, or authorized marine navigational track" in route_info["navigability_disclaimer"]
    assert "Electronic Navigational Charts (ENC)" in route_info["navigability_disclaimer"]


def test_e2e_fishing_evidence_insufficient_no_fish_invention(monkeypatch):
    """Test 7: Fishing zone returns INSUFFICIENT_EVIDENCE; does not invent fish locations or catch probabilities."""
    monkeypatch.setattr(orchestrator.agent.weather_agent, "analyze", AsyncMock(return_value=_make_dummy_weather()))
    monkeypatch.setattr(orchestrator.agent.ocean_agent, "analyze", AsyncMock(return_value=_make_dummy_ocean()))
    monkeypatch.setattr(orchestrator.agent.fishing_zone_agent, "analyze", AsyncMock(return_value=_make_dummy_fishing()))
    monkeypatch.setattr(orchestrator.agent.safety_risk_agent, "analyze", AsyncMock(return_value=_make_dummy_safety()))

    res = client.post(
        "/api/agents/orchestrator/analyze",
        json={
            "latitude": 15.0,
            "longitude": 72.0,
            "user_objective": "fishing",
            "target_species": "Mackerel",
        },
    )

    assert res.status_code == 200
    data = res.json()

    fish_info = data["derived_estimates"]["fisheries_suitability"]
    assert fish_info["zone_suitability"] == "INSUFFICIENT_EVIDENCE"
    assert fish_info["operational_feasibility_scope"] == "STRICTLY_PHYSICAL_WAVE_CONDITIONS"
    assert "UNVERIFIED" in fish_info["biological_distribution_status"]
    assert "Direct fish location" in fish_info["biological_distribution_status"]
    assert "Direct fish school distributions are unverified" in data["legal_disclaimer"]


def test_e2e_response_fields_consistency_with_frontend(monkeypatch):
    """Test 8: Verify all response fields between API and frontend contract are strictly present and typed."""
    monkeypatch.setattr(orchestrator.agent.weather_agent, "analyze", AsyncMock(return_value=_make_dummy_weather()))
    monkeypatch.setattr(orchestrator.agent.ocean_agent, "analyze", AsyncMock(return_value=_make_dummy_ocean()))
    monkeypatch.setattr(orchestrator.agent.fishing_zone_agent, "analyze", AsyncMock(return_value=_make_dummy_fishing()))
    monkeypatch.setattr(orchestrator.agent.route_agent, "analyze", AsyncMock(return_value=_make_dummy_route()))
    monkeypatch.setattr(orchestrator.agent.safety_risk_agent, "analyze", AsyncMock(return_value=_make_dummy_safety()))

    res = client.post(
        "/api/agents/orchestrator/analyze",
        json={
            "origin_latitude": 15.0,
            "origin_longitude": 72.0,
            "origin_name": "Goa Port",
            "destination_latitude": 18.9,
            "destination_longitude": 72.8,
            "destination_name": "Mumbai Port",
            "user_objective": "all",
        },
    )

    assert res.status_code == 200
    data = res.json()

    # Required top-level fields for frontend consumption
    required_fields = [
        "agent",
        "status",
        "user_objective",
        "location",
        "plan",
        "summary",
        "composite_safety_risk",
        "measured_observations",
        "derived_estimates",
        "individual_agent_results",
        "evidence_sources",
        "timestamps",
        "warnings",
        "missing_evidence",
        "errors",
        "recommendations",
        "legal_disclaimer",
        "generated_at",
    ]

    for field in required_fields:
        assert field in data, f"Required response field '{field}' missing from API response"

    # Type verifications matching frontend consumption
    assert isinstance(data["agent"], str)
    assert isinstance(data["status"], str)
    assert isinstance(data["location"], dict)
    assert isinstance(data["plan"], dict)
    assert isinstance(data["summary"], str)
    assert isinstance(data["composite_safety_risk"], dict)
    assert isinstance(data["measured_observations"], dict)
    assert isinstance(data["derived_estimates"], dict)
    assert isinstance(data["individual_agent_results"], dict)
    assert isinstance(data["evidence_sources"], list)
    assert isinstance(data["timestamps"], dict)
    assert isinstance(data["warnings"], list)
    assert isinstance(data["missing_evidence"], list)
    assert isinstance(data["errors"], dict)
    assert isinstance(data["recommendations"], list)
    assert isinstance(data["legal_disclaimer"], str)
    assert isinstance(data["generated_at"], str)
