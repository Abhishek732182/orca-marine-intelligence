"""Unit tests for independent Fishing Zone Agent (Agent 3).

Comprehensive test suite covering:
1. Valid fisheries evidence.
2. Missing fisheries data.
3. Missing or invalid environmental measurements.
4. Invalid coordinates and request parameters.
5. Provider timeout, unavailable provider, and malformed responses.
6. Unsupported target species.
7. No fabricated fish distributions or guaranteed catch claims.
8. Correct orchestrator propagation of UNKNOWN and INSUFFICIENT_EVIDENCE.
9. Transparent scoring without zero-substitution.
10. Species-specific thermal habitat preference boundaries.
"""

from datetime import datetime, timedelta, timezone
import pytest
import httpx
from unittest.mock import AsyncMock

from app.agents.fishing_zone_agent import FishingZoneAgent
from app.agents.orchestrator_agent import OrchestratorAgent
from app.schemas.agent_schemas import (
    FishingZoneAnalyzeRequest,
    OceanAnalyzeResponse,
    OrchestratorAnalyzeRequest,
    SafetyRiskAnalyzeResponse,
    WeatherAnalyzeResponse,
)
from app.schemas.evidence import EvidenceRecord


@pytest.fixture
def mock_marine_provider():
    provider = AsyncMock()
    provider.provider_name = "open-meteo-marine"
    return provider


# ==============================================================================
# Preserved Baseline Tests (Regression Safety)
# ==============================================================================

@pytest.mark.asyncio
async def test_fishing_zone_agent_operational_analysis(mock_marine_provider):
    now_utc = datetime.now(timezone.utc)
    mock_marine_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="fz-1",
            source="open-meteo-marine",
            source_record_id="rec-1",
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

    agent = FishingZoneAgent(provider=mock_marine_provider)
    request = FishingZoneAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        location_name="Goa Offshore Waters",
        target_species="Mackerel",
    )
    response = await agent.analyze(request)

    assert response.agent == "Fishing Zone Agent"
    assert response.status == "insufficient_evidence"
    assert response.observations["max_wave_height_m"] == 0.9
    assert response.analysis["operational_feasibility"] == "FAVORABLE"
    assert "Direct pelagic fish biomass" in response.warnings[0]
    assert "Official Potential Fishing Zone (PFZ) advisories require multi-spectral satellite" in response.analysis["fish_distribution_disclaimer"]
    # Evidence separation and safety checks
    assert "vessel_safety_notice" in response.analysis
    assert "does NOT determine vessel safety" in response.analysis["vessel_safety_notice"]
    assert response.analysis["verified_fish_distribution"]["status"] == "UNVERIFIED"
    assert response.analysis["physical_sea_conditions"]["max_wave_height_m"] == 0.9


@pytest.mark.asyncio
async def test_fishing_zone_agent_does_not_claim_safety_from_waves_alone(mock_marine_provider):
    now_utc = datetime.now(timezone.utc)
    mock_marine_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="fz-calm",
            source="open-meteo-marine",
            source_record_id="rec-calm",
            variable="wave_height",
            value=0.3,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        )
    ]
    agent = FishingZoneAgent(provider=mock_marine_provider)
    request = FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0)
    response = await agent.analyze(request)

    assert any("does NOT determine vessel or navigation safety" in w for w in response.warnings)
    assert "Wave height is a single physical factor and does NOT determine vessel safety" in response.analysis["vessel_safety_notice"]


@pytest.mark.asyncio
async def test_fishing_zone_agent_missing_coordinates(mock_marine_provider):
    agent = FishingZoneAgent(provider=mock_marine_provider)
    request = FishingZoneAnalyzeRequest()
    response = await agent.analyze(request)

    assert response.status == "insufficient_evidence"
    assert isinstance(response.error, str), f"Expected string error, got: {response.error!r}"
    assert "Coordinates required" in response.error


@pytest.mark.asyncio
async def test_fishing_zone_agent_empty_evidence_on_land(mock_marine_provider):
    mock_marine_provider.fetch.return_value = []

    agent = FishingZoneAgent(provider=mock_marine_provider)
    request = FishingZoneAnalyzeRequest(latitude=21.15, longitude=79.09)
    response = await agent.analyze(request)

    assert response.status == "insufficient_evidence"
    assert "inland or outside oceanographic grid" in response.warnings[1]


@pytest.mark.asyncio
async def test_fishing_zone_agent_provider_failure(mock_marine_provider):
    mock_marine_provider.fetch.side_effect = httpx.HTTPError("Service 503")

    agent = FishingZoneAgent(provider=mock_marine_provider)
    request = FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0)
    response = await agent.analyze(request)

    assert response.status == "error"
    assert isinstance(response.error, str), f"Expected string error, got: {response.error!r}"
    assert "Service 503" in response.error


# ==============================================================================
# 1. Valid Fisheries Evidence
# ==============================================================================

@pytest.mark.asyncio
async def test_fishing_zone_valid_fisheries_evidence(mock_marine_provider):
    """Test response when provider supplies verified biological and oceanographic evidence."""
    now_utc = datetime.now(timezone.utc)
    mock_marine_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="fz-wave-1",
            source="open-meteo-marine",
            source_record_id="wave-1",
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
            evidence_id="fz-sst-1",
            source="incois-pfz-satellite",
            source_record_id="sst-1",
            variable="sea_surface_temperature",
            value=28.2,
            unit="degC",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        ),
        EvidenceRecord(
            evidence_id="fz-chla-1",
            source="incois-pfz-satellite",
            source_record_id="chla-1",
            variable="chlorophyll_a",
            value=0.75,
            unit="mg/m^3",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        ),
        EvidenceRecord(
            evidence_id="fz-bio-1",
            source="cmfri-trawl-survey",
            source_record_id="bio-1",
            variable="fish_biomass",
            value=420.0,
            unit="kg/km^2",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        ),
    ]

    agent = FishingZoneAgent(provider=mock_marine_provider)
    request = FishingZoneAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        location_name="Goa Coastal Sector",
        target_species="Indian Mackerel",
    )
    response = await agent.analyze(request)

    assert response.status == "success"
    assert response.analysis["zone_suitability"] == "FAVORABLE"
    assert response.analysis["operational_feasibility"] == "FAVORABLE"
    assert response.analysis["verified_fish_distribution"]["status"] == "VERIFIED"
    assert response.analysis["verified_fish_distribution"]["biomass_data_available"] is True

    # Scoring verification
    scoring = response.analysis["scoring"]
    assert scoring["suitability_score"] is not None
    assert scoring["suitability_score"] >= 80.0
    assert scoring["evidence_coverage_pct"] == 100.0
    assert scoring["confidence_level"] == "HIGH"
    assert len(scoring["inputs_evaluated"]) == 3

    # Observations preservation
    obs = response.observations
    assert obs["max_wave_height_m"] == 0.8
    assert obs["sea_surface_temperature_c"] == 28.2
    assert obs["chlorophyll_a_mg_m3"] == 0.75
    assert obs["fish_biomass_kg_km2"] == 420.0


# ==============================================================================
# 2. Missing Fisheries Data (Standard Operational Grid Case)
# ==============================================================================

@pytest.mark.asyncio
async def test_fishing_zone_missing_fisheries_data(mock_marine_provider):
    """When only physical wave telemetry is available, biological indicators must be unverified."""
    now_utc = datetime.now(timezone.utc)
    mock_marine_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="fz-wave-only",
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

    agent = FishingZoneAgent(provider=mock_marine_provider)
    request = FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0, target_species="Tuna")
    response = await agent.analyze(request)

    assert response.status == "insufficient_evidence"
    assert response.analysis["zone_suitability"] == "INSUFFICIENT_EVIDENCE"
    assert response.analysis["scoring"]["suitability_score"] is None
    assert response.analysis["scoring"]["confidence_level"] == "INSUFFICIENT_EVIDENCE"
    assert response.analysis["scoring"]["evidence_coverage_pct"] == 0.0
    assert response.analysis["verified_fish_distribution"]["status"] == "UNVERIFIED"
    assert response.analysis["verified_fish_distribution"]["catch_probability"] is None
    assert response.analysis["verified_fish_distribution"]["biomass_data_available"] is False

    # Identified missing providers
    ds = response.data_source
    assert "INCOIS Potential Fishing Zone (PFZ) advisory service" in ds["missing_providers"]
    assert any("Copernicus" in p for p in ds["missing_providers"])
    assert len(ds["recommended_integrations"]) > 0


# ==============================================================================
# 3. Missing or Invalid Environmental Measurements
# ==============================================================================

@pytest.mark.asyncio
async def test_fishing_zone_missing_or_invalid_environmental_measurements(mock_marine_provider):
    """Verify that null, negative, or invalid measurements are handled without crash or zero substitution."""
    now_utc = datetime.now(timezone.utc)
    mock_marine_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="rec-null",
            source="open-meteo-marine",
            source_record_id="null-1",
            variable="wave_height",
            value=None,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="missing",
        ),
        EvidenceRecord(
            evidence_id="rec-neg",
            source="open-meteo-marine",
            source_record_id="neg-1",
            variable="wave_height",
            value=-3.5,  # Physically invalid
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        ),
        EvidenceRecord(
            evidence_id="rec-valid",
            source="open-meteo-marine",
            source_record_id="valid-1",
            variable="wave_height",
            value=1.4,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        ),
    ]

    agent = FishingZoneAgent(provider=mock_marine_provider)
    request = FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0)
    response = await agent.analyze(request)

    # Negative and null records are excluded, valid record 1.4 m is processed
    assert response.observations["max_wave_height_m"] == 1.4
    assert any("One or more wave height records were null or physically invalid" in w for w in response.warnings)
    # Missing values are NOT treated as 0.0
    assert response.observations["avg_wave_height_m"] == 1.4


@pytest.mark.asyncio
async def test_fishing_zone_all_measurements_null(mock_marine_provider):
    """When all wave measurements are null, agent returns insufficient_evidence."""
    now_utc = datetime.now(timezone.utc)
    mock_marine_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="rec-null-1",
            source="open-meteo-marine",
            source_record_id="null-1",
            variable="wave_height",
            value=None,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="missing",
        )
    ]

    agent = FishingZoneAgent(provider=mock_marine_provider)
    request = FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0)
    response = await agent.analyze(request)

    assert response.status == "insufficient_evidence"
    assert "Null wave height records." in response.warnings


# ==============================================================================
# 4. Invalid Coordinates and Request Parameters
# ==============================================================================

@pytest.mark.asyncio
async def test_fishing_zone_out_of_bounds_coordinates(mock_marine_provider):
    """Coordinates outside physical geographic bounds raise ValueError."""
    agent = FishingZoneAgent(provider=mock_marine_provider)

    # 1. Pydantic request schema rejects invalid coordinates
    with pytest.raises(ValueError):
        FishingZoneAnalyzeRequest(latitude=95.0, longitude=72.0)

    with pytest.raises(ValueError):
        FishingZoneAnalyzeRequest(latitude=15.0, longitude=190.0)

    # 2. Agent analyze internal guard rejects constructed request
    constructed_lat = FishingZoneAnalyzeRequest.model_construct(latitude=95.0, longitude=72.0)
    with pytest.raises(ValueError, match="Invalid coordinates"):
        await agent.analyze(constructed_lat)

    constructed_lon = FishingZoneAnalyzeRequest.model_construct(latitude=15.0, longitude=190.0)
    with pytest.raises(ValueError, match="Invalid coordinates"):
        await agent.analyze(constructed_lon)


# ==============================================================================
# 5. Provider Timeout, Unavailable Provider, and Malformed Responses
# ==============================================================================

@pytest.mark.asyncio
async def test_fishing_zone_provider_timeout(mock_marine_provider):
    """Provider network timeout returns error status with detailed message."""
    mock_marine_provider.fetch.side_effect = httpx.TimeoutException("Read timed out after 20.0s")

    agent = FishingZoneAgent(provider=mock_marine_provider)
    request = FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0)
    response = await agent.analyze(request)

    assert response.status == "error"
    assert response.error is not None
    assert "Read timed out" in response.error


@pytest.mark.asyncio
async def test_fishing_zone_malformed_provider_response(mock_marine_provider):
    """Malformed provider payload raises clean error response instead of unhandled crash."""
    mock_marine_provider.fetch.side_effect = ValueError("Unexpected Open-Meteo hourly response structure")

    agent = FishingZoneAgent(provider=mock_marine_provider)
    request = FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0)
    response = await agent.analyze(request)

    assert response.status == "error"
    assert response.error is not None
    assert "Unexpected Open-Meteo hourly response" in response.error


# ==============================================================================
# 6. Unsupported Target Species
# ==============================================================================

@pytest.mark.asyncio
async def test_fishing_zone_unsupported_target_species(mock_marine_provider):
    """Target species not in registry is flagged as UNSUPPORTED without fabricating thermal bounds."""
    now_utc = datetime.now(timezone.utc)
    mock_marine_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="fz-w",
            source="open-meteo-marine",
            source_record_id="w-1",
            variable="wave_height",
            value=0.8,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        )
    ]

    agent = FishingZoneAgent(provider=mock_marine_provider)
    request = FishingZoneAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        target_species="Arctic Cod",
    )
    response = await agent.analyze(request)

    assert response.analysis["target_species_status"] == "UNSUPPORTED"
    assert any("Unsupported target species 'Arctic Cod'" in w for w in response.warnings)
    # Does not crash or invent fake optimal ranges


# ==============================================================================
# 7. No Fabricated Fish Distributions or Guaranteed Catch Claims
# ==============================================================================

@pytest.mark.asyncio
async def test_fishing_zone_no_fabricated_distributions(mock_marine_provider):
    """Assert catch_probability is strictly None, and no fake coordinates or biomass are invented."""
    now_utc = datetime.now(timezone.utc)
    mock_marine_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="fz-calm",
            source="open-meteo-marine",
            source_record_id="rec-calm",
            variable="wave_height",
            value=0.5,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        )
    ]

    agent = FishingZoneAgent(provider=mock_marine_provider)
    request = FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0)
    response = await agent.analyze(request)

    dist = response.analysis["verified_fish_distribution"]
    assert dist["status"] == "UNVERIFIED"
    assert dist["catch_probability"] is None
    assert dist["biomass_data_available"] is False
    assert "Official Potential Fishing Zone (PFZ) advisories require multi-spectral satellite" in response.analysis["fish_distribution_disclaimer"]


# ==============================================================================
# 8. Correct Orchestrator Propagation of UNKNOWN and INSUFFICIENT_EVIDENCE
# ==============================================================================

@pytest.mark.asyncio
async def test_orchestrator_propagates_fishing_insufficient_evidence():
    """Verify Orchestrator Agent (Agent 6) captures and propagates Fishing Zone insufficient evidence."""
    mock_w = AsyncMock()
    mock_w.analyze.return_value = WeatherAnalyzeResponse(
        agent="Weather Agent",
        status="success",
        location={"location_name": "Offshore Goa", "latitude": 15.0, "longitude": 72.0},
        data_source={"provider": "Open-Meteo Weather"},
        observations={"wind_speed_knots": 12.0, "temperature_c": 28.0},
        forecast=[],
        analysis={},
    )
    mock_o = AsyncMock()
    mock_o.analyze.return_value = OceanAnalyzeResponse(
        agent="Ocean Agent",
        status="success",
        location={"location_name": "Offshore Goa", "latitude": 15.0, "longitude": 72.0},
        data_source={"provider": "Open-Meteo Marine"},
        observations={"wave_height_m": 1.1},
        analysis={"wmo_sea_state": {"code": 3, "description": "Slight"}},
    )
    mock_sr = AsyncMock()
    mock_sr.analyze.return_value = SafetyRiskAnalyzeResponse(
        agent="Safety/Risk Agent",
        status="success",
        location={"location_name": "Offshore Goa", "latitude": 15.0, "longitude": 72.0},
        data_source={"providers_attempted": ["Open-Meteo Marine"]},
        observations={"wave_height_m": 1.1, "wind_speed_knots": 12.0},
        analysis={"risk_category": "MODERATE", "risk_score": 35},
    )

    # Real FishingZoneAgent returning insufficient_evidence
    mock_provider = AsyncMock()
    mock_provider.provider_name = "open-meteo-marine"
    mock_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="fz-1",
            source="open-meteo-marine",
            source_record_id="rec-1",
            variable="wave_height",
            value=1.1,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=datetime.now(timezone.utc),
            retrieved_at=datetime.now(timezone.utc),
            status="valid",
        )
    ]
    real_fishing_agent = FishingZoneAgent(provider=mock_provider)

    orchestrator = OrchestratorAgent(
        weather_agent=mock_w,
        ocean_agent=mock_o,
        fishing_zone_agent=real_fishing_agent,
        safety_risk_agent=mock_sr,
    )

    req = OrchestratorAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        user_objective="fishing",
        vessel_type="small_craft",
        target_species="Mackerel",
    )
    res = await orchestrator.analyze(req)

    # Specialist result preserved
    assert res.individual_agent_results["fishing_zone"]["status"] == "insufficient_evidence"
    # Missing evidence explicitly includes fishing zone note
    assert any("Fishing Zone" in item for item in res.missing_evidence)
    # Fisheries suitability correctly records insufficient evidence
    f_suit = res.derived_estimates["fisheries_suitability"]
    assert f_suit["zone_suitability"] == "INSUFFICIENT_EVIDENCE"
    assert "UNVERIFIED" in f_suit["biological_distribution_status"]
    # Warnings are propagated
    assert any("Direct pelagic fish biomass" in w for w in res.warnings)


# ==============================================================================
# 9. Transparent Scoring Without Zero-Substitution
# ==============================================================================

@pytest.mark.asyncio
async def test_fishing_zone_transparent_scoring_dynamic_weights(mock_marine_provider):
    """When valid SST and Chlorophyll are available but biomass is missing,

    weights are dynamically normalized and missing biomass is NOT assigned zero.
    """
    now_utc = datetime.now(timezone.utc)
    mock_marine_provider.fetch.return_value = [
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
        ),
        EvidenceRecord(
            evidence_id="fz-sst-1",
            source="satellite-sst",
            source_record_id="sst-1",
            variable="sea_surface_temperature",
            value=28.0,  # Optimal for Indian Mackerel (26-30 °C) -> sub_score 95.0
            unit="degC",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        ),
        EvidenceRecord(
            evidence_id="fz-chla-1",
            source="sentinel-3-olci",
            source_record_id="chla-1",
            variable="chlorophyll_a",
            value=0.8,  # Optimal mesotrophic (0.2-2.5 mg/m3) -> sub_score 90.0
            unit="mg/m^3",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        ),
    ]

    agent = FishingZoneAgent(provider=mock_marine_provider)
    request = FishingZoneAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        target_species="Indian Mackerel",
    )
    response = await agent.analyze(request)

    assert response.status == "success"
    scoring = response.analysis["scoring"]
    # 2 inputs evaluated (SST and Chl-a)
    assert len(scoring["inputs_evaluated"]) == 2
    assert "fish_biomass" in scoring["missing_inputs"]
    # Score should be ~92.5 (normalized between 95 and 90), NOT ~64 (which would occur if missing biomass was converted to 0)
    assert scoring["suitability_score"] is not None
    assert scoring["suitability_score"] >= 90.0
    assert scoring["evidence_coverage_pct"] == 66.7


# ==============================================================================
# 10. Species-Specific Thermal Boundaries
# ==============================================================================

@pytest.mark.asyncio
async def test_fishing_zone_species_thermal_boundaries(mock_marine_provider):
    """Verify species thermal suitability matches documented scientific bounds."""
    now_utc = datetime.now(timezone.utc)

    # 1. Indian Mackerel in optimal 28 °C waters
    mock_marine_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="w-1",
            source="open-meteo-marine",
            source_record_id="w-1",
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
            evidence_id="sst-opt",
            source="satellite-sst",
            source_record_id="sst-1",
            variable="sea_surface_temperature",
            value=28.0,
            unit="degC",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        ),
        EvidenceRecord(
            evidence_id="bio-1",
            source="cmfri-trawl",
            source_record_id="b-1",
            variable="fish_biomass",
            value=350.0,
            unit="kg/km^2",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        ),
    ]

    agent = FishingZoneAgent(provider=mock_marine_provider)
    res_opt = await agent.analyze(
        FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0, target_species="Mackerel")
    )
    assert res_opt.analysis["zone_suitability"] == "FAVORABLE"
    assert any("Optimal SST range" in c for c in res_opt.analysis["criteria_applied"])

    # 2. Indian Mackerel in thermal stress (34 °C waters - exceeds tolerable 31.5 °C)
    mock_marine_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="w-1",
            source="open-meteo-marine",
            source_record_id="w-1",
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
            evidence_id="sst-stress",
            source="satellite-sst",
            source_record_id="sst-2",
            variable="sea_surface_temperature",
            value=34.0,  # Unfavorable thermal stress
            unit="degC",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        ),
        EvidenceRecord(
            evidence_id="bio-1",
            source="cmfri-trawl",
            source_record_id="b-1",
            variable="fish_biomass",
            value=50.0,
            unit="kg/km^2",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        ),
    ]

    res_stress = await agent.analyze(
        FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0, target_species="Mackerel")
    )
    assert res_stress.analysis["zone_suitability"] == "UNFAVORABLE"


# ==============================================================================
# 11. Stale Evidence Rejection Under Documented Freshness Rules
# ==============================================================================

@pytest.mark.asyncio
async def test_fishing_zone_stale_evidence_rejected(mock_marine_provider):
    """Verify records older than documented freshness thresholds are rejected.

    SST older than 6h and biomass older than 7d must not be used to calculate a score.
    """
    from datetime import timedelta
    now_utc = datetime.now(timezone.utc)
    stale_sst_time = now_utc - timedelta(hours=10)   # Exceeds 6h max age
    stale_bio_time = now_utc - timedelta(days=14)   # Exceeds 7d max age

    mock_marine_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="w-fresh",
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
        ),
        EvidenceRecord(
            evidence_id="sst-stale",
            source="incois-pfz-satellite",
            source_record_id="sst-old",
            variable="sea_surface_temperature",
            value=28.2,
            unit="degC",
            latitude=15.0,
            longitude=72.0,
            observed_at=stale_sst_time,
            retrieved_at=now_utc,
            status="valid",
        ),
        EvidenceRecord(
            evidence_id="bio-stale",
            source="cmfri-trawl-survey",
            source_record_id="bio-old",
            variable="fish_biomass",
            value=420.0,
            unit="kg/km^2",
            latitude=15.0,
            longitude=72.0,
            observed_at=stale_bio_time,
            retrieved_at=now_utc,
            status="valid",
        ),
    ]

    agent = FishingZoneAgent(provider=mock_marine_provider)
    req = FishingZoneAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        target_species="Indian Mackerel",
    )
    res = await agent.analyze(req)

    # Stale biological records must be rejected; result must be insufficient_evidence
    assert res.status == "insufficient_evidence"
    assert res.analysis["zone_suitability"] == "INSUFFICIENT_EVIDENCE"
    assert res.analysis["scoring"]["suitability_score"] is None
    assert res.analysis["scoring"]["evidence_coverage_pct"] == 0.0
    assert res.analysis["verified_fish_distribution"]["status"] == "UNVERIFIED"

    # Provenance for rejected variables must remain None
    prov = res.observations["evidence_provenance"]
    assert prov["sea_surface_temperature"] is None
    assert prov["fish_biomass"] is None
    assert prov["wave_height"] is not None

    # Warning explicitly flags rejected stale records
    assert any("rejected as stale or invalid" in w for w in res.warnings)


# ==============================================================================
# 12. Synthetic / Invalid Status Records Are Rejected
# ==============================================================================

@pytest.mark.asyncio
async def test_fishing_zone_synthetic_invalid_records_rejected(mock_marine_provider):
    """Records with status != 'valid' or missing values must be rejected."""
    now_utc = datetime.now(timezone.utc)
    mock_marine_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="w-1",
            source="open-meteo-marine",
            source_record_id="w-1",
            variable="wave_height",
            value=1.0,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        ),
        EvidenceRecord(
            evidence_id="bio-fake",
            source="synthetic-feed",
            source_record_id="fake-1",
            variable="fish_biomass",
            value=500.0,
            unit="kg/km^2",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="invalid",  # Invalid status
        ),
    ]

    agent = FishingZoneAgent(provider=mock_marine_provider)
    res = await agent.analyze(FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0))

    assert res.status == "insufficient_evidence"
    assert res.analysis["verified_fish_distribution"]["status"] == "UNVERIFIED"
    assert res.observations["fish_biomass_kg_km2"] is None
    assert res.observations["evidence_provenance"]["fish_biomass"] is None


# ==============================================================================
# 13. Repeated Requests Consistency (Determinism)
# ==============================================================================

@pytest.mark.asyncio
async def test_fishing_zone_repeated_requests_consistency(mock_marine_provider):
    """Repeated queries with identical inputs and provider evidence produce identical outputs."""
    now_utc = datetime.now(timezone.utc)
    records = [
        EvidenceRecord(
            evidence_id="w-rep-1",
            source="open-meteo-marine",
            source_record_id="w-1",
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
    mock_marine_provider.fetch.return_value = records

    agent = FishingZoneAgent(provider=mock_marine_provider)
    req = FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0, location_name="Goa Offshore Waters")

    res1 = await agent.analyze(req)
    res2 = await agent.analyze(req)

    assert res1.status == res2.status
    assert res1.observations["max_wave_height_m"] == res2.observations["max_wave_height_m"]
    assert res1.analysis["zone_suitability"] == res2.analysis["zone_suitability"]
    assert res1.analysis["operational_feasibility"] == res2.analysis["operational_feasibility"]
    assert res1.warnings == res2.warnings
    assert res1.location == res2.location


# ==============================================================================
# 14. Geographic Disambiguation (Goa Offshore Waters vs Goa Coastal Sector)
# ==============================================================================

@pytest.mark.asyncio
async def test_fishing_zone_geographic_disambiguation(mock_marine_provider):
    """Coordinates (15.0°N, 72.0°E) are ~185 km offshore; location must clarify distinction."""
    now_utc = datetime.now(timezone.utc)
    mock_marine_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="w-1",
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

    agent = FishingZoneAgent(provider=mock_marine_provider)
    res = await agent.analyze(FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0))

    loc = res.location
    assert loc is not None
    assert "geographic_characterization" in loc
    geo = loc["geographic_characterization"]
    assert "Offshore" in geo["sector_classification"]
    assert geo["distance_to_nearest_coastline_km"] >= 180.0
    assert "Goa Coastal Sector" in geo["nomenclature_distinction"]
    assert "Goa Offshore Waters" in geo["nomenclature_distinction"]


# ==============================================================================
# 15. Provenance Preservation for Every Observed Value
# ==============================================================================

@pytest.mark.asyncio
async def test_fishing_zone_provenance_preservation(mock_marine_provider):
    """Verify provider, timestamp, coordinates, and units are preserved in evidence_provenance."""
    now_utc = datetime.now(timezone.utc)
    mock_marine_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="w-prov-1",
            source="open-meteo-marine",
            source_record_id="w-prov-rec-1",
            variable="wave_height",
            value=0.85,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
            quality_flags=["forecast_data"],
        )
    ]

    agent = FishingZoneAgent(provider=mock_marine_provider)
    res = await agent.analyze(FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0))

    prov = res.observations["evidence_provenance"]
    assert prov["wave_height"] is not None
    wave_prov = prov["wave_height"]
    assert wave_prov["source"] == "open-meteo-marine"
    assert wave_prov["evidence_id"] == "w-prov-1"
    assert wave_prov["unit"] == "m"
    assert wave_prov["latitude"] == 15.0
    assert wave_prov["longitude"] == 72.0
    assert wave_prov["observed_at"] == now_utc.isoformat()
    assert "open-meteo-marine" in res.data_source["contributing_sources"]


# ==============================================================================
# 16. Seven Fresh vs 17 Stale Records & Forecast Window Coverage
# ==============================================================================

@pytest.mark.asyncio
async def test_fishing_zone_24_records_freshness_and_stale_rejection(mock_marine_provider):
    """Verify that in a 24-record batch:
    - 17 stale records (> 3h old) are rejected and excluded from calculations.
    - 7 fresh records (recent nowcast + future forecast) are accepted and span the window.
    - hours_evaluated is derived from the observation time span, NOT record count.
    - Rejected records are documented with explicit rejection reasons.
    """
    now = datetime.now(timezone.utc)
    records: list[EvidenceRecord] = []

    # 17 stale past observations (> 3h old) with high wave values (4.5 m)
    # If these were mistakenly included, max wave would be 4.5 m (HAZARDOUS).
    for i in range(17):
        stale_time = now - timedelta(hours=3.5 + i)
        records.append(
            EvidenceRecord(
                evidence_id=f"stale-{i}",
                source="open-meteo-marine",
                source_record_id=f"stale-rec-{i}",
                variable="wave_height",
                value=4.5,
                unit="m",
                latitude=15.0,
                longitude=72.0,
                observed_at=stale_time,
                retrieved_at=now,
                status="valid",
            )
        )

    # 3 fresh recent observations (< 3h old) with calm wave values
    for j, hrs_ago in enumerate([2.0, 1.0, 0.25]):
        fresh_recent_time = now - timedelta(hours=hrs_ago)
        records.append(
            EvidenceRecord(
                evidence_id=f"fresh-recent-{j}",
                source="open-meteo-marine",
                source_record_id=f"fresh-recent-rec-{j}",
                variable="wave_height",
                value=0.8,
                unit="m",
                latitude=15.0,
                longitude=72.0,
                observed_at=fresh_recent_time,
                retrieved_at=now,
                status="valid",
            )
        )

    # 4 fresh future forecast observations with forecast_data flag
    # Spanning from now + 1h to now + 4h
    for k, hrs_ahead in enumerate([1.0, 2.0, 3.0, 4.0]):
        future_time = now + timedelta(hours=hrs_ahead)
        records.append(
            EvidenceRecord(
                evidence_id=f"fresh-future-{k}",
                source="open-meteo-marine",
                source_record_id=f"fresh-future-rec-{k}",
                variable="wave_height",
                value=1.0,
                unit="m",
                latitude=15.0,
                longitude=72.0,
                observed_at=future_time,
                retrieved_at=now,
                status="valid",
                quality_flags=["forecast_data"],
            )
        )

    mock_marine_provider.fetch.return_value = records

    agent = FishingZoneAgent(provider=mock_marine_provider)
    res = await agent.analyze(
        FishingZoneAnalyzeRequest(
            latitude=15.0,
            longitude=72.0,
            forecast_time_window_hours=24,
        )
    )

    # Status must reflect missing biological fisheries data
    assert res.status == "insufficient_evidence"
    assert res.analysis["zone_suitability"] == "INSUFFICIENT_EVIDENCE"

    # Exactly 17 records rejected, exactly 7 records accepted
    assert res.data_source["rejected_records_count"] == 17
    assert res.observations["rejected_records_count"] == 17
    assert res.observations["accepted_records_count"] == 7
    assert len(res.data_source["rejected_records"]) == 17

    # Every rejected record explicitly notes staleness
    assert all("stale" in r["reason"].lower() for r in res.data_source["rejected_records"])
    assert any("rejected as stale or invalid" in w for w in res.warnings)

    # Stale 4.5m wave records MUST NOT contaminate wave calculations!
    # Valid heights are three 0.8m and four 1.0m records -> max = 1.0m, avg = (3*0.8 + 4*1.0)/7 = 0.91m
    assert res.observations["max_wave_height_m"] == 1.0
    assert res.observations["avg_wave_height_m"] == pytest.approx(0.91, abs=0.02)
    assert res.analysis["operational_feasibility"] == "FAVORABLE"

    # Time span between earliest accepted (now - 2h) and latest accepted (now + 4h) is 6.0 hours.
    # hours_evaluated MUST NOT equal record count (6.0 != 7)!
    assert res.observations["hours_evaluated"] == 6.0
    assert res.observations["accepted_records_count"] == 7
    assert res.observations["hours_evaluated"] != res.observations["accepted_records_count"]
    assert res.observations["forecast_window_hours_requested"] == 24
    assert res.observations["forecast_window_hours_covered"] == 6.0


# ==============================================================================
# 17. Hours Evaluated Is Independent of Record Count (Frequency Agnostic)
# ==============================================================================

@pytest.mark.asyncio
async def test_fishing_zone_hours_evaluated_independent_of_record_count(mock_marine_provider):
    """Verify that 9 half-hourly records evaluate to 4.0 hours, NOT 9 hours."""
    now = datetime.now(timezone.utc)
    records: list[EvidenceRecord] = []

    # 9 half-hourly records spaced 30 mins apart (from now to now + 4.0 hours)
    for i in range(9):
        obs_time = now + timedelta(minutes=30 * i)
        records.append(
            EvidenceRecord(
                evidence_id=f"step-{i}",
                source="open-meteo-marine",
                source_record_id=f"rec-{i}",
                variable="wave_height",
                value=0.7 + (i * 0.02),
                unit="m",
                latitude=15.0,
                longitude=72.0,
                observed_at=obs_time,
                retrieved_at=now,
                status="valid",
                quality_flags=["forecast_data"],
            )
        )

    mock_marine_provider.fetch.return_value = records

    agent = FishingZoneAgent(provider=mock_marine_provider)
    res = await agent.analyze(
        FishingZoneAnalyzeRequest(
            latitude=15.0,
            longitude=72.0,
            forecast_time_window_hours=12,
        )
    )

    # Accepted count is 9, but time span is 4.0 hours
    assert res.observations["accepted_records_count"] == 9
    assert res.observations["hours_evaluated"] == 4.0
    assert res.observations["hours_evaluated"] != res.observations["accepted_records_count"]
    assert res.observations["forecast_window_hours_covered"] == 4.0


# ==============================================================================
# 18. Calculations Exclude All Rejected and Invalid Records
# ==============================================================================

@pytest.mark.asyncio
async def test_fishing_zone_calculations_exclude_all_invalid_records(mock_marine_provider):
    """Verify that null, out-of-range, negative, and invalid-status records are completely excluded."""
    now = datetime.now(timezone.utc)
    records = [
        # Valid fresh record 1
        EvidenceRecord(
            evidence_id="val-1",
            source="open-meteo-marine",
            source_record_id="v1",
            variable="wave_height",
            value=0.8,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now,
            retrieved_at=now,
            status="valid",
        ),
        # Valid fresh record 2
        EvidenceRecord(
            evidence_id="val-2",
            source="open-meteo-marine",
            source_record_id="v2",
            variable="wave_height",
            value=1.2,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now + timedelta(hours=1),
            retrieved_at=now,
            status="valid",
            quality_flags=["forecast_data"],
        ),
        # Stale record (must be excluded)
        EvidenceRecord(
            evidence_id="stale-wave",
            source="open-meteo-marine",
            source_record_id="s1",
            variable="wave_height",
            value=5.0,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now - timedelta(hours=10),
            retrieved_at=now,
            status="valid",
        ),
        # Physically impossible negative wave (must be excluded)
        EvidenceRecord(
            evidence_id="neg-wave",
            source="open-meteo-marine",
            source_record_id="n1",
            variable="wave_height",
            value=-1.5,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now,
            retrieved_at=now,
            status="valid",
        ),
        # Out-of-bounds wave (must be excluded)
        EvidenceRecord(
            evidence_id="huge-wave",
            source="open-meteo-marine",
            source_record_id="h1",
            variable="wave_height",
            value=45.0,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now,
            retrieved_at=now,
            status="valid",
        ),
        # Invalid status record (must be excluded)
        EvidenceRecord(
            evidence_id="bad-status",
            source="open-meteo-marine",
            source_record_id="b1",
            variable="wave_height",
            value=3.5,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now,
            retrieved_at=now,
            status="invalid",
        ),
    ]

    mock_marine_provider.fetch.return_value = records

    agent = FishingZoneAgent(provider=mock_marine_provider)
    res = await agent.analyze(FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0))

    # Only the two valid records (0.8 and 1.2) must enter calculations
    assert res.observations["accepted_records_count"] == 2
    assert res.observations["rejected_records_count"] == 4
    assert res.observations["max_wave_height_m"] == 1.2
    assert res.observations["avg_wave_height_m"] == 1.0

    # Verify that rejection reasons are preserved
    reasons = res.data_source["rejected_records_reasons"]
    assert any("stale" in r.lower() for r in reasons)
    assert any("physically invalid" in r.lower() for r in reasons)
    assert any("not 'valid'" in r.lower() for r in reasons)


# ==============================================================================
# 19. Operational Feasibility Explicitly Scoped to Physical Wave Conditions Only
# ==============================================================================

@pytest.mark.asyncio
async def test_fishing_zone_operational_feasibility_limited_to_wave_physics(mock_marine_provider):
    """Ensure operational_feasibility: FAVORABLE is explicitly scoped to wave physics only."""
    now = datetime.now(timezone.utc)
    mock_marine_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="calm-1",
            source="open-meteo-marine",
            source_record_id="c1",
            variable="wave_height",
            value=0.75,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now,
            retrieved_at=now,
            status="valid",
        )
    ]

    agent = FishingZoneAgent(provider=mock_marine_provider)
    res = await agent.analyze(FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0))

    assert res.analysis["operational_feasibility"] == "FAVORABLE"
    assert res.analysis["operational_feasibility_scope"] == "STRICTLY_PHYSICAL_WAVE_CONDITIONS"
    assert "does NOT grant vessel safety clearance" in res.analysis["operational_feasibility_disclaimer"]
    assert "Wave height is a single physical factor and does NOT determine vessel safety" in res.analysis["vessel_safety_notice"]
    assert "strictly limited to physical wave conditions; NOT vessel safety clearance" in res.analysis["zone_summary"]
    assert any("NOT guaranteed catches or vessel safety clearance" in w for w in res.warnings)


# ==============================================================================
# 20. Strict Missing Biological Data Preservation (No Fabrication)
# ==============================================================================

@pytest.mark.asyncio
async def test_fishing_zone_missing_biological_data_strict_preservation(mock_marine_provider):
    """When only wave data is present, no biological variables or scores are fabricated."""
    now = datetime.now(timezone.utc)
    mock_marine_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="w-only",
            source="open-meteo-marine",
            source_record_id="wo1",
            variable="wave_height",
            value=1.0,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now,
            retrieved_at=now,
            status="valid",
        )
    ]

    agent = FishingZoneAgent(provider=mock_marine_provider)
    res = await agent.analyze(
        FishingZoneAnalyzeRequest(
            latitude=15.0,
            longitude=72.0,
            target_species="Indian Mackerel",
        )
    )

    # Core statuses
    assert res.status == "insufficient_evidence"
    assert res.analysis["zone_suitability"] == "INSUFFICIENT_EVIDENCE"
    assert res.analysis["scoring"]["suitability_score"] is None
    assert res.analysis["scoring"]["evidence_coverage_pct"] == 0.0

    # Unverified fish distribution
    verified_dist = res.analysis["verified_fish_distribution"]
    assert verified_dist["status"] == "UNVERIFIED"
    assert verified_dist["biomass_data_available"] is False
    assert verified_dist["catch_probability"] is None
    assert "coordinates cannot be confirmed" in res.analysis["zone_summary"] or "cannot be guaranteed or invented" in verified_dist["statement"]

    # Biological observations must strictly be None
    obs = res.observations
    assert obs["sea_surface_temperature_c"] is None
    assert obs["chlorophyll_a_mg_m3"] is None
    assert obs["fish_biomass_kg_km2"] is None

    # Provenance for missing biological variables must be None
    prov = obs["evidence_provenance"]
    assert prov["sea_surface_temperature"] is None
    assert prov["chlorophyll_a"] is None
    assert prov["fish_biomass"] is None
    assert prov["wave_height"] is not None


@pytest.mark.asyncio
async def test_fishing_zone_agent_operational_vs_biological_evidence_separation(mock_marine_provider):
    """Verify wave-based operational feasibility is evaluated strictly separately from biological fish evidence."""
    now = datetime.now(timezone.utc)
    mock_marine_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="fz-sep-1",
            source="open-meteo-marine",
            source_record_id="rec-sep-1",
            variable="wave_height",
            value=1.1,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now,
            retrieved_at=now,
            status="valid",
        )
    ]

    agent = FishingZoneAgent(provider=mock_marine_provider)
    res = await agent.analyze(FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0))

    # Operational feasibility scope must be strictly physical wave conditions
    assert res.analysis["operational_feasibility_scope"] == "STRICTLY_PHYSICAL_WAVE_CONDITIONS"
    assert res.analysis["operational_feasibility"] in ("FAVORABLE", "MODERATE / CAUTION")

    # Separately, biological fish telemetry must be INSUFFICIENT_EVIDENCE / UNVERIFIED
    assert res.status == "insufficient_evidence"
    assert res.analysis["zone_suitability"] == "INSUFFICIENT_EVIDENCE"
    assert res.analysis["verified_fish_distribution"]["status"] == "UNVERIFIED"

    # Vessel safety notice must confirm wave height does not establish vessel safety alone
    assert "Wave height is a single physical factor and does NOT determine vessel safety" in res.analysis["vessel_safety_notice"]


@pytest.mark.asyncio
async def test_fishing_zone_agent_prevention_of_unsupported_claims(mock_marine_provider):
    """Verify FishingZoneAgent never fabricates fish locations, biomass, chlorophyll-a, or catch probabilities."""
    now = datetime.now(timezone.utc)
    mock_marine_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="fz-unsupp-1",
            source="open-meteo-marine",
            source_record_id="rec-unsupp-1",
            variable="wave_height",
            value=1.5,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now,
            retrieved_at=now,
            status="valid",
        )
    ]

    agent = FishingZoneAgent(provider=mock_marine_provider)
    res = await agent.analyze(FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0, target_species="Pomfret"))

    # Never fabricate biological values
    assert res.observations["chlorophyll_a_mg_m3"] is None
    assert res.observations["fish_biomass_kg_km2"] is None
    assert res.observations["sea_surface_temperature_c"] is None
    assert res.analysis["verified_fish_distribution"]["catch_probability"] is None

    # Never fabricate numerical suitability score when biological evidence is missing
    assert res.analysis["scoring"]["suitability_score"] is None
    assert res.analysis["scoring"]["evidence_coverage_pct"] == 0.0

    # Retain disclaimer
    disclaimer = res.analysis["fish_distribution_disclaimer"]
    assert "ORCA does not invent or simulate unverified fish coordinates" in disclaimer


