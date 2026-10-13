"""Targeted tests for ORCA agent architecture improvements.

Validates:
1. Specialist task delegation (all vs targeted subsets, execution tracking).
2. Partial provider failure (graceful degradation, error preservation, partial_failure status).
3. Stale evidence handling (provenance freshness status, never substituted as fresh).
4. Conflicting evidence detection (WMO code vs wave height discrepancy, conflict warnings).
5. Unsupported fish-prediction claims (environmental suitability strictly separated from fish presence,
   catch probability is None, biomass prediction is None).
6. Non-navigational geodesic route and wave non-clearance disclaimers.
7. Structured advisory completeness (conditions, evidence, uncertainty, limitations, safety warnings).
"""

from unittest.mock import AsyncMock, patch
import pytest

from app.agents.orchestrator_agent import OrchestratorAgent, LEGAL_DISCLAIMER
from app.agents.fishing_zone_agent import FishingZoneAgent
from app.agents.route_agent import RouteAgent
from app.agents.mission_synthesizer import synthesize_mission_advisory
from app.schemas.agent_schemas import (
    FishingZoneAnalyzeRequest,
    FishingZoneAnalyzeResponse,
    OceanAnalyzeResponse,
    OrchestratorAnalyzeRequest,
    OrchestratorAnalyzeResponse,
    RouteAnalyzeRequest,
    RouteAnalyzeResponse,
    SafetyRiskAnalyzeResponse,
    WeatherAnalyzeResponse,
)


def _make_dummy_weather(status="success", temp=28.0, wind_kts=16.0, wind_dir=240.0, precip=0.0):
    return WeatherAnalyzeResponse(
        agent="Weather Agent",
        status=status,
        location={"location_name": "Offshore Goa", "latitude": 15.0, "longitude": 72.0},
        data_source={"provider": "Open-Meteo Weather", "endpoint": "https://api.open-meteo.com/v1/forecast"},
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
        data_source={"provider": "Open-Meteo Marine", "attribution": "ECMWF / Meteo-France"},
        observations={"wave_height_m": wave_h, "sample_count": 24},
        analysis={"wmo_sea_state": {"code": wmo_code, "description": wmo_desc}},
        warnings=[],
    )


def _make_dummy_fishing(status="success", suitability="FAVORABLE", feasibility="FAVORABLE"):
    return FishingZoneAnalyzeResponse(
        agent="Fishing Zone Agent",
        status=status,
        location={"location_name": "Offshore Goa", "latitude": 15.0, "longitude": 72.0},
        data_source={"provider": "Open-Meteo Marine", "connected_providers": ["open-meteo-marine"]},
        observations={"wave_height_m": 1.4},
        analysis={
            "zone_suitability": suitability,
            "operational_feasibility": feasibility,
            "operational_feasibility_scope": "STRICTLY_PHYSICAL_WAVE_CONDITIONS",
            "verified_fish_distribution": {
                "status": "UNVERIFIED",
                "biomass_data_available": False,
                "catch_probability": None,
                "biomass_prediction": None,
                "statement": "Direct fish location telemetry is unavailable from numerical models.",
                "environmental_suitability_distinction": "Environmental habitat suitability reflects physical/biochemical parameters only.",
            },
            "scoring": {
                "suitability_score": None,
                "confidence_level": "INSUFFICIENT_EVIDENCE",
                "evidence_coverage_pct": 0.0,
            },
        },
        warnings=[],
    )


def _make_dummy_route(status="success", dist_km=430.5, dist_nm=232.4, hours=19.4):
    return RouteAnalyzeResponse(
        agent="Route Agent",
        status=status,
        location={"origin": "Offshore Goa", "destination": "Mumbai Port"},
        data_source={
            "calculation_method": "Haversine Great-Circle geodesic formula",
            "routing_type": "straight_line_geodesic",
            "limitations": "Geodesic calculation without bathymetry, nautical hazards, or land avoidance.",
        },
        observations={"total_distance_km": dist_km, "total_distance_nm": dist_nm, "waypoint_count": 0},
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
            "risk_reasons": ["Moderate wave heights present."],
            "recommendations": ["Exercise watchfulness in offshore corridor."],
        },
        warnings=[],
    )


@pytest.mark.asyncio
async def test_delegation_subset_and_full_dispatch():
    """Verify task delegation respects planned specialists and tracks execution accurately."""
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

    # 1. Targeted delegation: 'safety_check' invokes weather and safety_risk only
    req_safety = OrchestratorAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        user_objective="safety_check",
    )
    res_safety = await orchestrator.analyze(req_safety)

    assert "weather" in res_safety.plan["planned_agents"]
    assert "safety_risk" in res_safety.plan["planned_agents"]
    assert "fishing_zone" not in res_safety.plan["planned_agents"]
    assert "route" not in res_safety.plan["planned_agents"]
    assert mock_weather.analyze.await_count == 1
    assert mock_safety.analyze.await_count == 1
    assert mock_fishing.analyze.await_count == 0
    assert mock_route.analyze.await_count == 0

    # 2. Targeted delegation: 'passage_planning' invokes route, ocean, weather, safety_risk
    mock_weather.reset_mock()
    mock_safety.reset_mock()
    req_route = OrchestratorAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        destination_latitude=18.9,
        destination_longitude=72.8,
        user_objective="passage_planning",
    )
    res_route = await orchestrator.analyze(req_route)
    assert "route" in res_route.plan["planned_agents"]
    assert mock_route.analyze.await_count == 1
    assert mock_fishing.analyze.await_count == 0


@pytest.mark.asyncio
async def test_partial_provider_failure_handling():
    """Verify orchestrator gracefully degrades on partial specialist failure without crashing."""
    mock_weather = AsyncMock()
    mock_weather.analyze.return_value = _make_dummy_weather()
    # Ocean agent encounters upstream HTTP timeout
    mock_ocean = AsyncMock()
    mock_ocean.analyze.side_effect = RuntimeError("Open-Meteo Marine HTTP 504 Gateway Timeout")
    # Fishing zone reports insufficient evidence
    mock_fishing = AsyncMock()
    mock_fishing.analyze.return_value = FishingZoneAnalyzeResponse(
        agent="Fishing Zone Agent",
        status="insufficient_evidence",
        location={"location_name": "Offshore Goa", "latitude": 15.0, "longitude": 72.0},
        data_source={"provider": "Open-Meteo Marine"},
        observations={},
        analysis={"zone_suitability": "INSUFFICIENT_EVIDENCE"},
        error="Missing valid marine grid points.",
    )
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
        user_objective="all",
        destination_latitude=18.9,
        destination_longitude=72.8,
    )
    res = await orchestrator.analyze(req)

    # Status must be partial_failure, not crashed or total failure
    assert res.status == "partial_failure"
    assert "ocean" in res.errors
    assert "RuntimeError" in res.errors["ocean"]
    assert "ocean" in res.plan["failed_agents"]
    # Successful agents must still be present
    assert "weather" in res.individual_agent_results
    assert res.individual_agent_results["weather"]["status"] == "success"
    # Missing evidence must record fishing zone gap
    assert any("Fishing Zone" in m for m in res.missing_evidence)


@pytest.mark.asyncio
async def test_stale_evidence_handling_and_preservation():
    """Verify stale evidence records are flagged with freshness_status='stale' and never treated as fresh."""
    mock_weather = AsyncMock()
    mock_weather.analyze.return_value = _make_dummy_weather()

    # Safety agent flagged with stale observation warning
    stale_safety = _make_dummy_safety()
    stale_safety.warnings = ["Marine observation retrieval timestamp is stale (> 24 hours old)."]
    mock_safety = AsyncMock()
    mock_safety.analyze.return_value = stale_safety

    orchestrator = OrchestratorAgent(
        weather_agent=mock_weather,
        safety_risk_agent=mock_safety,
    )

    req = OrchestratorAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        user_objective="safety_check",
    )
    res = await orchestrator.analyze(req)

    # Check evidence sources carry freshness status
    safety_source = next((s for s in res.evidence_sources if s["agent"] == "Safety/Risk Agent"), None)
    assert safety_source is not None
    assert safety_source["freshness_status"] == "stale"
    assert "observation_time" in safety_source
    assert "retrieval_time" in safety_source
    assert "source_limitations" in safety_source


@pytest.mark.asyncio
async def test_conflicting_evidence_detection():
    """Verify conflict between wave height (Rough) and reported WMO Code (Slight) is detected and flagged."""
    mock_weather = AsyncMock()
    mock_weather.analyze.return_value = _make_dummy_weather()
    # 2.8m wave height is WMO Code 5 (Rough), but dummy reports WMO Code 3 (Slight)
    mock_ocean = AsyncMock()
    mock_ocean.analyze.return_value = _make_dummy_ocean(wave_h=2.8, wmo_code=3, wmo_desc="Slight (0.5 - 1.25 m)")
    mock_safety = AsyncMock()
    mock_safety.analyze.return_value = _make_dummy_safety(risk_category="HIGH", wave_h=2.8)

    orchestrator = OrchestratorAgent(
        weather_agent=mock_weather,
        ocean_agent=mock_ocean,
        safety_risk_agent=mock_safety,
    )

    req = OrchestratorAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        user_objective="all",
    )
    res = await orchestrator.analyze(req)

    # Discrepancy warning must be captured in warnings
    assert any("Observation discrepancy" in w for w in res.warnings)
    assert "wmo_discrepancy_warning" in res.measured_observations
    # Original provider data must NOT be fabricated or overwritten
    assert res.measured_observations["wave_height_m"] == 2.8
    assert res.measured_observations["wmo_sea_state_code"] == 3


@pytest.mark.asyncio
async def test_unsupported_fish_prediction_claims_rejected():
    """Verify environmental suitability is strictly separated from fish presence, catch probability, and biomass."""
    mock_weather = AsyncMock()
    mock_weather.analyze.return_value = _make_dummy_weather()
    mock_fishing = AsyncMock()
    mock_fishing.analyze.return_value = _make_dummy_fishing(suitability="FAVORABLE", feasibility="FAVORABLE")

    orchestrator = OrchestratorAgent(
        weather_agent=mock_weather,
        fishing_zone_agent=mock_fishing,
    )

    req = OrchestratorAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        user_objective="fishing",
    )
    res = await orchestrator.analyze(req)

    fz_estimates = res.derived_estimates["fisheries_suitability"]
    # Catch probability and biomass prediction must be strictly None
    assert fz_estimates["catch_probability"] is None
    assert fz_estimates["biomass_prediction"] is None
    assert fz_estimates["actual_fish_presence"] == "UNVERIFIED"
    assert "CRITICAL NOTICE" in fz_estimates["environmental_suitability_distinction"]
    assert "NOT indicate actual fish presence" in fz_estimates["environmental_suitability_distinction"]


@pytest.mark.asyncio
async def test_llm_synthesis_guardrail_rejects_hallucinated_catch_probabilities():
    """Verify LLM guardrail forces deterministic fallback if LLM invents catch probability or certified route."""
    measured = {"wave_height_m": 1.2, "wind_speed_knots": 10.0}
    derived = {
        "fisheries_suitability": {
            "zone_suitability": "FAVORABLE",
            "operational_feasibility": "FAVORABLE",
        },
        "geodesic_route": {
            "distance_km": 100.0,
            "distance_nm": 54.0,
        },
    }
    safety = {"risk_category": "LOW", "status_headline": "FAVORABLE"}

    # Mock LLM returning hallucinated catch probability
    hallucinated_text = "Conditions are great. Catch probability: 85% for Indian Mackerel with guaranteed catch."
    with patch("app.agents.mission_synthesizer.call_chat_llm", AsyncMock(return_value=(hallucinated_text, "llm"))):
        text, mode = await synthesize_mission_advisory(
            location_name="Offshore Goa",
            latitude=15.0,
            longitude=72.0,
            user_objective="fishing",
            vessel_type="small_craft",
            measured_observations=measured,
            derived_estimates=derived,
            composite_safety_risk=safety,
            warnings=[],
            missing_evidence=[],
            errors={},
            recommendations=["Exercise vigilance."],
        )
        # Must fall back to deterministic mode
        assert mode == "deterministic"
        assert "Catch probability: 85%" not in text


@pytest.mark.asyncio
async def test_route_and_wave_disclaimers():
    """Verify route is explicitly non-certified geodesic estimate and wave height is not safety clearance."""
    route_agent = RouteAgent()
    req = RouteAnalyzeRequest(
        origin_latitude=15.0,
        origin_longitude=72.0,
        destination_latitude=18.9,
        destination_longitude=72.8,
        origin_name="Goa",
        destination_name="Mumbai",
    )
    res = await route_agent.analyze(req)

    assert res.observations["is_verified_navigable_route"] is False
    assert res.analysis["route_classification"] == "GEODESIC_STRAIGHT_LINE"
    assert any("geodesic straight-line distance" in w for w in res.warnings)
    assert any("DOES NOT replace Electronic Navigational Charts" in w for w in res.warnings)


@pytest.mark.asyncio
async def test_structured_advisory_contains_required_sections():
    """Verify response structure contains conditions, evidence, uncertainty, limitations, and safety warnings."""
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
        destination_latitude=18.9,
        destination_longitude=72.8,
        user_objective="all",
    )
    res = await orchestrator.analyze(req)

    # 1. Conditions
    assert "wave_height_m" in res.measured_observations
    assert "wind_speed_knots" in res.measured_observations
    # 2. Evidence with provenance & freshness
    assert len(res.evidence_sources) > 0
    for src in res.evidence_sources:
        assert "freshness_status" in src
        assert "provenance" in src
        assert "source_limitations" in src
    # 3. Uncertainty & limitations
    assert isinstance(res.missing_evidence, list)
    assert res.legal_disclaimer == LEGAL_DISCLAIMER
    # 4. Safety warnings & wave non-clearance
    assert "wave_clearance_notice" in res.composite_safety_risk
    assert "does NOT constitute vessel safety clearance" in res.composite_safety_risk["wave_clearance_notice"]
