"""Unit and workflow integration tests for Biological Prediction Agent.

Covers:
1. Pure unit tests for evidence freshness and non-fabrication.
2. FishingZoneAgent integration with missing biological evidence.
3. FishingZoneAgent integration with stale chlorophyll evidence.
4. FishingZoneAgent integration with fresh wave evidence without fish observations.
5. Backward compatibility of all existing fishing-zone response fields.
6. OrchestratorAgent propagation of biological prediction status and safeguards.
7. Provider failures and missing environmental data.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
import httpx
import pytest

from app.agents.biological_prediction_agent import (
    EnvironmentalEvidence,
    analyze_environment,
)
from app.agents.fishing_zone_agent import FishingZoneAgent
from app.agents.orchestrator_agent import OrchestratorAgent
from app.schemas.agent_schemas import (
    FishingZoneAnalyzeRequest,
    FishingZoneAnalyzeResponse,
    OceanAnalyzeResponse,
    OrchestratorAnalyzeRequest,
    RouteAnalyzeResponse,
    SafetyRiskAnalyzeResponse,
    WeatherAnalyzeResponse,
)
from app.schemas.evidence import EvidenceRecord


# ==============================================================================
# Pure Module Unit Tests
# ==============================================================================

def test_missing_evidence_does_not_predict_fish():
    result = analyze_environment(
        EnvironmentalEvidence(),
        now=datetime(2026, 10, 13, tzinfo=timezone.utc),
    )

    assert result["fish_presence"] == "UNVERIFIED"
    assert result["catch_probability"] is None
    assert result["biomass_prediction"] is None
    assert result["predictive_accuracy"] == "NOT_EVALUABLE"
    assert result["fresh_variable_count"] == 0


def test_stale_chlorophyll_is_not_fresh_evidence():
    result = analyze_environment(
        EnvironmentalEvidence(
            chlorophyll_a_mg_m3=0.4,
            chlorophyll_observed_at=datetime(
                2026, 10, 1, tzinfo=timezone.utc
            ),
            chlorophyll_source="NOAA ERDDAP",
        ),
        now=datetime(2026, 10, 13, tzinfo=timezone.utc),
    )

    assert result["environmental_evidence"]["chlorophyll_a"] == "STALE"
    assert result["fish_presence"] == "UNVERIFIED"
    assert result["catch_probability"] is None


def test_fresh_environmental_data_is_not_proof_of_fish():
    result = analyze_environment(
        EnvironmentalEvidence(
            wave_height_m=1.2,
            wave_observed_at=datetime(
                2026, 10, 13, tzinfo=timezone.utc
            ),
            wave_source="Open-Meteo Marine",
        ),
        now=datetime(2026, 10, 13, tzinfo=timezone.utc),
    )

    assert result["environmental_evidence"]["wave_height"] == "FRESH"
    assert result["environmental_evidence_completeness_pct"] == 33
    assert result["fish_presence"] == "UNVERIFIED"
    assert result["catch_probability"] is None


# ==============================================================================
# Workflow Integration Tests: FishingZoneAgent
# ==============================================================================

@pytest.fixture
def mock_provider():
    provider = AsyncMock()
    provider.provider_name = "open-meteo-marine"
    return provider


@pytest.mark.asyncio
async def test_fishing_zone_integration_missing_biological_evidence(mock_provider):
    """Verify that when only wave data is present, biological evidence is marked UNAVAILABLE and fish presence UNVERIFIED."""
    now_utc = datetime.now(timezone.utc)
    mock_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="fz-wave-1",
            source="open-meteo-marine",
            source_record_id="w-1",
            variable="wave_height",
            value=0.9,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        )
    ]

    agent = FishingZoneAgent(provider=mock_provider)
    req = FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0, target_species="Mackerel")
    resp = await agent.analyze(req)

    assert resp.status == "insufficient_evidence"
    assert "biological_prediction" in resp.analysis

    bio = resp.analysis["biological_prediction"]
    assert bio["status"] == "ENVIRONMENTAL_EVIDENCE_AVAILABLE"
    assert bio["environmental_evidence"]["wave_height"] == "FRESH"
    assert bio["environmental_evidence"]["chlorophyll_a"] == "UNAVAILABLE"
    assert bio["environmental_evidence"]["sea_surface_temperature"] == "UNAVAILABLE"
    assert bio["fresh_variable_count"] == 1
    assert bio["fish_presence"] == "UNVERIFIED"
    assert bio["catch_probability"] is None
    assert bio["biomass_prediction"] is None
    assert bio["predictive_accuracy"] == "NOT_EVALUABLE"
    assert bio["score_type"] == "ENVIRONMENTAL_DATA_COMPLETENESS_ONLY"


@pytest.mark.asyncio
async def test_fishing_zone_integration_stale_chlorophyll_evidence(mock_provider):
    """Verify that stale chlorophyll observations are marked STALE and excluded from fresh counts."""
    now_utc = datetime.now(timezone.utc)
    mock_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="fz-wave-fresh",
            source="open-meteo-marine",
            source_record_id="w-fresh",
            variable="wave_height",
            value=0.8,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        ),
        EvidenceRecord(
            evidence_id="fz-chla-stale",
            source="NOAA ERDDAP",
            source_record_id="chla-old",
            variable="chlorophyll_a",
            value=0.45,
            unit="mg/m^3",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc - timedelta(days=10),
            retrieved_at=now_utc,
            status="valid",
        ),
    ]

    agent = FishingZoneAgent(provider=mock_provider)
    req = FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0, target_species="Mackerel")
    resp = await agent.analyze(req)

    bio = resp.analysis["biological_prediction"]
    assert bio["environmental_evidence"]["chlorophyll_a"] == "STALE"
    assert bio["environmental_evidence"]["wave_height"] == "FRESH"
    assert bio["fresh_variable_count"] == 1
    assert bio["fish_presence"] == "UNVERIFIED"
    assert bio["catch_probability"] is None
    assert bio["biomass_prediction"] is None


@pytest.mark.asyncio
async def test_fishing_zone_integration_backward_compatibility(mock_provider):
    """Verify that all existing fishing-zone response fields and invariants remain strictly preserved."""
    now_utc = datetime.now(timezone.utc)
    mock_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="fz-compat",
            source="open-meteo-marine",
            source_record_id="w-compat",
            variable="wave_height",
            value=0.7,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        )
    ]

    agent = FishingZoneAgent(provider=mock_provider)
    req = FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0, target_species="Mackerel")
    resp = await agent.analyze(req)

    assert resp.agent == "Fishing Zone Agent"
    assert resp.analysis["operational_feasibility"] == "FAVORABLE"
    assert resp.analysis["zone_suitability"] == "INSUFFICIENT_EVIDENCE"
    assert resp.analysis["verified_fish_distribution"]["status"] == "UNVERIFIED"
    assert resp.analysis["verified_fish_distribution"]["catch_probability"] is None
    assert resp.analysis["verified_fish_distribution"]["biomass_prediction"] is None
    assert "vessel_safety_notice" in resp.analysis
    assert "fish_distribution_disclaimer" in resp.analysis
    assert resp.analysis["physical_sea_conditions"]["max_wave_height_m"] == 0.7


@pytest.mark.asyncio
async def test_fishing_zone_integration_provider_failure(mock_provider):
    """Verify that provider failure leaves biological evidence UNAVAILABLE and safe."""
    mock_provider.fetch.side_effect = httpx.HTTPError("Service 503 Gateway Timeout")

    agent = FishingZoneAgent(provider=mock_provider)
    req = FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0)
    resp = await agent.analyze(req)

    assert resp.status == "error"
    bio = resp.analysis["biological_prediction"]
    assert bio["status"] == "INSUFFICIENT_FRESH_EVIDENCE"
    assert bio["fresh_variable_count"] == 0
    assert bio["environmental_evidence"]["wave_height"] == "UNAVAILABLE"
    assert bio["fish_presence"] == "UNVERIFIED"
    assert bio["catch_probability"] is None
    assert bio["predictive_accuracy"] == "NOT_EVALUABLE"


@pytest.mark.asyncio
async def test_fishing_zone_integration_empty_evidence_on_land(mock_provider):
    """Verify that inland coordinates with no marine cells return INSUFFICIENT_FRESH_EVIDENCE."""
    mock_provider.fetch.return_value = []

    agent = FishingZoneAgent(provider=mock_provider)
    req = FishingZoneAnalyzeRequest(latitude=21.15, longitude=79.09)
    resp = await agent.analyze(req)

    assert resp.status == "insufficient_evidence"
    bio = resp.analysis["biological_prediction"]
    assert bio["status"] == "INSUFFICIENT_FRESH_EVIDENCE"
    assert bio["fresh_variable_count"] == 0
    assert bio["fish_presence"] == "UNVERIFIED"
    assert bio["catch_probability"] is None


# ==============================================================================
# Workflow Integration Tests: OrchestratorAgent Propagation
# ==============================================================================

@pytest.mark.asyncio
async def test_orchestrator_integration_propagates_biological_status():
    """Verify that the orchestrator synthesizes and propagates biological evidence status and non-fabrication safeguards."""
    now_utc = datetime.now(timezone.utc)

    mock_weather = AsyncMock()
    mock_weather.analyze.return_value = WeatherAnalyzeResponse(
        agent="Weather Agent",
        status="success",
        location={"latitude": 15.0, "longitude": 72.0},
        data_source={"provider": "Open-Meteo Weather"},
        observations={"temperature_c": 28.0, "wind_speed_knots": 12.0, "wind_direction_deg": 240.0, "precipitation_mm": 0.0},
        forecast=[],
        analysis={"wind_regime": "Gentle breeze"},
        warnings=[],
    )

    mock_ocean = AsyncMock()
    mock_ocean.analyze.return_value = OceanAnalyzeResponse(
        agent="Ocean Agent",
        status="success",
        location={"latitude": 15.0, "longitude": 72.0},
        data_source={"provider": "Open-Meteo Marine"},
        observations={"wave_height_m": 1.1, "sample_count": 24},
        analysis={"wmo_sea_state": {"code": 3, "description": "Slight (0.5 - 1.25 m)"}},
        warnings=[],
    )

    mock_route = AsyncMock()
    mock_route.analyze.return_value = RouteAnalyzeResponse(
        agent="Route Agent",
        status="success",
        location={"origin": "Offshore Goa", "destination": "Mumbai Port"},
        data_source={"calculation_method": "Haversine Great-Circle geodesic formula"},
        observations={"total_distance_km": 440.0, "total_distance_nm": 237.5, "waypoint_count": 2},
        analysis={"estimated_transit_hours": 19.8},
        warnings=["Straight-line geodesic distance only."],
    )

    mock_safety = AsyncMock()
    mock_safety.analyze.return_value = SafetyRiskAnalyzeResponse(
        agent="Safety/Risk Agent",
        status="success",
        location={"latitude": 15.0, "longitude": 72.0},
        data_source={"providers_attempted": ["Open-Meteo Marine"]},
        observations={"wave_height_m": 1.1, "wind_speed_knots": 12.0, "precipitation_mm": 0.0},
        analysis={"risk_category": "LOW", "risk_score": 25, "risk_reasons": ["Favorable baseline conditions."], "recommendations": ["Safe operational baseline."]},
        warnings=[],
    )

    mock_fishing_provider = AsyncMock()
    mock_fishing_provider.provider_name = "open-meteo-marine"
    mock_fishing_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="fz-rec-1",
            source="open-meteo-marine",
            source_record_id="rec-1",
            variable="wave_height",
            value=1.1,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        )
    ]
    real_fishing_agent = FishingZoneAgent(provider=mock_fishing_provider)

    orchestrator = OrchestratorAgent(
        weather_agent=mock_weather,
        ocean_agent=mock_ocean,
        fishing_zone_agent=real_fishing_agent,
        route_agent=mock_route,
        safety_risk_agent=mock_safety,
    )

    req = OrchestratorAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        user_objective="all",
        vessel_type="small_craft",
        target_species="Mackerel",
        destination_latitude=18.9,
        destination_longitude=72.8,
    )

    resp = await orchestrator.analyze(req)

    assert resp.status == "success"
    fisheries = resp.derived_estimates["fisheries_suitability"]

    # Verify non-fabrication safeguards
    assert fisheries["actual_fish_presence"] == "UNVERIFIED"
    assert fisheries["catch_probability"] is None
    assert fisheries["biomass_prediction"] is None
    assert fisheries["predictive_accuracy"] == "NOT_EVALUABLE"

    # Verify biological status propagation
    assert fisheries["biological_evidence_status"] == "ENVIRONMENTAL_EVIDENCE_AVAILABLE"
    assert fisheries["biological_prediction"] is not None
    assert fisheries["biological_prediction"]["environmental_evidence"]["wave_height"] == "FRESH"
    assert fisheries["biological_prediction"]["environmental_evidence"]["chlorophyll_a"] == "UNAVAILABLE"
