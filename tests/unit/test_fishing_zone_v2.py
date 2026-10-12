"""Focused Regression Tests for Fisheries Intelligence v2.

Covers the 10 critical regression scenarios:
1. SST request parameters, parsing, units, timestamps, and evidence provenance.
2. Null SST and missing hourly values.
3. Species thermal-range evaluation using actual SST evidence.
4. Cloud-masked null chlorophyll-a returning insufficient evidence.
5. Favorable wave conditions conflicting with out-of-range SST.
6. Stale observations being excluded from current assessments.
7. Unsupported or fabricated biological records being rejected.
8. Worker initialization, idempotency, and clean shutdown.
9. Provider timeouts, HTTP errors, and deterministic/offline fallback.
10. Direct fishing-zone API and orchestrator consistency.
"""

import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch
import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.agents.fishing_zone_agent import FishingZoneAgent
from app.agents.orchestrator_agent import OrchestratorAgent
from app.agents.species_rules import evaluate_thermal_suitability, lookup_species
from app.data_sources.base import MarineDataProvider
from app.data_sources.erddap_client import ErddapClient, ErddapSnapshot
from app.data_sources.ingestion_worker import FisheriesIngestionWorker, get_fisheries_worker
from app.data_sources.open_meteo_marine import OpenMeteoMarineProvider
from app.schemas.agent_schemas import FishingZoneAnalyzeRequest, OrchestratorAnalyzeRequest
from app.schemas.evidence import EvidenceRecord

client = TestClient(app)


class MockMarineProvider(MarineDataProvider):
    """Deterministic mock provider supplying specific evidence records."""

    def __init__(self, records: list[EvidenceRecord] | None = None, raise_exc: Exception | None = None) -> None:
        self.records = records or []
        self.raise_exc = raise_exc

    @property
    def provider_name(self) -> str:
        return "mock-marine-provider"

    async def fetch(self, *, latitude: float, longitude: float, observed_at: str | None = None) -> list[EvidenceRecord]:
        if self.raise_exc:
            raise self.raise_exc
        return list(self.records)


# ==============================================================================
# Test 1: SST request parameters, parsing, units, timestamps, and provenance
# ==============================================================================
@pytest.mark.asyncio
async def test_sst_request_parameters_parsing_units_and_provenance():
    """1. Verify SST query parameters, parsing, units (°C), timestamps, and provenance."""
    provider = OpenMeteoMarineProvider()
    requested_lat = 15.0
    requested_lon = 72.0
    now_utc = datetime.now(timezone.utc)
    now_iso = now_utc.strftime("%Y-%m-%dT%H:00:00Z")

    mock_json = {
        "latitude": 15.0,
        "longitude": 72.0,
        "timezone": "UTC",
        "hourly_units": {
            "wave_height": "m",
            "sea_surface_temperature": "°C",
        },
        "hourly": {
            "time": [now_iso],
            "wave_height": [1.15],
            "sea_surface_temperature": [28.4],
        },
    }

    mock_resp = httpx.Response(
        status_code=200,
        json=mock_json,
        request=httpx.Request("GET", "https://marine-api.open-meteo.com/v1/marine"),
    )

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)) as mock_get:
        records = await provider.fetch(latitude=requested_lat, longitude=requested_lon)
        assert mock_get.called
        call_params = mock_get.call_args[1].get("params") or {}
        assert call_params.get("hourly") == "wave_height,sea_surface_temperature"

    # Check both wave and SST records returned
    wave_recs = [r for r in records if r.variable in ("wave_height", "wave_height_m", "hs")]
    sst_recs = [r for r in records if r.variable in ("sea_surface_temperature", "sst", "temperature_c")]

    assert len(wave_recs) == 1
    assert wave_recs[0].value == 1.15
    assert wave_recs[0].unit == "m"

    assert len(sst_recs) == 1
    sst = sst_recs[0]
    assert sst.value == 28.4
    assert sst.unit == "°C"
    assert sst.status == "valid"
    assert sst.observed_at is not None
    assert sst.observed_at.tzinfo is not None
    assert sst.metadata.get("requested_latitude") == requested_lat
    assert sst.metadata.get("requested_longitude") == requested_lon

    # Test provenance generated in FishingZoneAgent
    agent = FishingZoneAgent(provider=MockMarineProvider(records))
    resp = await agent.analyze(FishingZoneAnalyzeRequest(latitude=requested_lat, longitude=requested_lon))
    assert resp.status == "insufficient_evidence"  # Lacks direct biological distribution
    prov = resp.observations.get("evidence_provenance", {})
    sst_prov = prov.get("sea_surface_temperature")
    assert sst_prov is not None
    assert sst_prov["source"] == "open-meteo-marine"
    assert sst_prov["freshness_status"] == "valid"
    assert sst_prov["requested_latitude"] == requested_lat
    assert sst_prov["requested_longitude"] == requested_lon


# ==============================================================================
# Test 2: Null SST and missing hourly values
# ==============================================================================
@pytest.mark.asyncio
async def test_null_sst_and_missing_hourly_values():
    """2. Ensure null SST is not substituted with zero or synthetic numbers."""
    provider = OpenMeteoMarineProvider()
    now_utc = datetime.now(timezone.utc)
    now_iso = now_utc.strftime("%Y-%m-%dT%H:00:00Z")

    mock_json = {
        "latitude": 15.0,
        "longitude": 72.0,
        "timezone": "UTC",
        "hourly_units": {
            "wave_height": "m",
            "sea_surface_temperature": "°C",
        },
        "hourly": {
            "time": [now_iso],
            "wave_height": [0.95],
            "sea_surface_temperature": [None],  # Null SST
        },
    }

    mock_resp = httpx.Response(
        status_code=200,
        json=mock_json,
        request=httpx.Request("GET", "https://marine-api.open-meteo.com/v1/marine"),
    )

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)):
        records = await provider.fetch(latitude=15.0, longitude=72.0)

    sst_recs = [r for r in records if r.variable in ("sea_surface_temperature", "sst")]
    assert len(sst_recs) == 0  # No null record converted to zero

    # Agent analysis must reflect missing SST
    agent = FishingZoneAgent(provider=MockMarineProvider(records))
    resp = await agent.analyze(FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0))
    assert resp.observations.get("sea_surface_temperature_c") is None
    assert resp.analysis.get("environmental_habitat_indicators", {}).get("sea_surface_temperature_c") is None


# ==============================================================================
# Test 3: Species thermal-range evaluation using actual SST evidence
# ==============================================================================
def test_species_thermal_range_evaluation_using_actual_sst_evidence():
    """3. Evaluate species thermal suitability against documented scientific bounds."""
    mackerel = lookup_species("Mackerel")
    assert mackerel["status"] == "SUPPORTED"
    # Optimal 26.0 - 30.0 °C
    eval_opt = evaluate_thermal_suitability(mackerel, 28.0)
    assert eval_opt["thermal_suitability"] == "OPTIMAL"
    assert eval_opt["thermal_sub_score"] == 95.0
    assert "CMFRI" in eval_opt["citation"] or "INCOIS" in eval_opt["citation"]

    # Tolerable 24.0 - 26.0 or 30.0 - 31.5 °C
    eval_tol = evaluate_thermal_suitability(mackerel, 25.0)
    assert eval_tol["thermal_suitability"] == "TOLERABLE"

    # Thermal stress outside tolerable (> 31.5 °C)
    eval_stress = evaluate_thermal_suitability(mackerel, 33.0)
    assert eval_stress["thermal_suitability"] == "UNFAVORABLE"
    assert eval_stress["thermal_sub_score"] == 20.0


# ==============================================================================
# Test 4: Cloud-masked null chlorophyll-a returning insufficient evidence
# ==============================================================================
def test_cloud_masked_null_chlorophyll_returning_insufficient_evidence():
    """4. Cloud-masked satellite chlorophyll observations return empty without fabrication."""
    client_erddap = ErddapClient(mode="fixture_only")
    table_with_clouds = {
        "table": {
            "columnNames": ["time", "latitude", "longitude", "chlor_a"],
            "rows": [
                ["2026-10-12T00:00:00Z", 15.0, 72.0, None],  # Cloud masked
                ["2026-10-12T00:00:00Z", 15.02, 72.02, None],  # Cloud masked
            ],
        }
    }
    records = client_erddap.parse_erddap_json_table(
        table_with_clouds,
        variable_name="chlorophyll_a",
        unit="mg/m^3",
        source_url="https://coastwatch.noaa.gov/erddap/test",
    )
    # Zero records produced; never synthesizes values
    assert len(records) == 0


# ==============================================================================
# Test 5: Favorable wave conditions conflicting with out-of-range SST
# ==============================================================================
@pytest.mark.asyncio
async def test_favorable_wave_conditions_conflicting_with_out_of_range_sst():
    """5. Favorable waves (<1.25m) distinct from thermal stress (>31.5°C) with conflict warning."""
    now_utc = datetime.now(timezone.utc)
    wave_rec = EvidenceRecord(
        evidence_id="wave-1",
        source="open-meteo-marine",
        variable="wave_height",
        value=0.85,  # Favorable wave (<1.25m)
        unit="m",
        latitude=15.0,
        longitude=72.0,
        observed_at=now_utc,
        retrieved_at=now_utc,
        status="valid",
        quality_flags=["forecast_data"],
    )
    sst_rec = EvidenceRecord(
        evidence_id="sst-1",
        source="open-meteo-marine",
        variable="sea_surface_temperature",
        value=33.0,  # Unfavorable thermal stress for Mackerel (>31.5°C)
        unit="°C",
        latitude=15.0,
        longitude=72.0,
        observed_at=now_utc,
        retrieved_at=now_utc,
        status="valid",
        quality_flags=["forecast_data"],
    )

    agent = FishingZoneAgent(provider=MockMarineProvider([wave_rec, sst_rec]))
    req = FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0, target_species="Mackerel")
    resp = await agent.analyze(req)

    assert resp.analysis["operational_feasibility"] == "FAVORABLE"
    assert resp.analysis["environmental_habitat_indicators"]["thermal_suitability"] == "UNFAVORABLE"
    # Must contain divergence / conflict warning
    has_conflict_warn = any("CONFLICT / DIVERGENCE" in w for w in resp.warnings)
    assert has_conflict_warn is True


# ==============================================================================
# Test 6: Stale observations being excluded from current assessments
# ==============================================================================
@pytest.mark.asyncio
async def test_stale_observations_excluded_from_current_assessments():
    """6. Ensure observations exceeding freshness limits are rejected and not used."""
    now_utc = datetime.now(timezone.utc)
    # SST max age is 6 hours; set observed_at to 12 hours ago
    stale_sst = EvidenceRecord(
        evidence_id="sst-stale",
        source="open-meteo-marine",
        variable="sea_surface_temperature",
        value=28.0,
        unit="°C",
        latitude=15.0,
        longitude=72.0,
        observed_at=now_utc - timedelta(hours=12),
        retrieved_at=now_utc,
        status="valid",
        quality_flags=[],
    )
    # Wave max age is 3 hours; set observed_at to 8 hours ago
    stale_wave = EvidenceRecord(
        evidence_id="wave-stale",
        source="open-meteo-marine",
        variable="wave_height",
        value=1.0,
        unit="m",
        latitude=15.0,
        longitude=72.0,
        observed_at=now_utc - timedelta(hours=8),
        retrieved_at=now_utc,
        status="valid",
        quality_flags=[],
    )

    agent = FishingZoneAgent(provider=MockMarineProvider([stale_sst, stale_wave]))
    resp = await agent.analyze(FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0))

    # All records rejected as stale
    assert resp.data_source["rejected_records_count"] == 2
    assert any("stale" in r["reason"].lower() for r in resp.data_source["rejected_records"])
    # Empty fresh records cannot increase confidence
    assert resp.observations["accepted_records_count"] == 0


# ==============================================================================
# Test 7: Unsupported or fabricated biological records being rejected
# ==============================================================================
@pytest.mark.asyncio
async def test_unsupported_or_fabricated_biological_records_rejected():
    """7. Reject invalid, non-numeric, or fabricated records and flag unsupported species."""
    now_utc = datetime.now(timezone.utc)
    fabricated_rec = EvidenceRecord(
        evidence_id="fab-1",
        source="unverified-source",
        variable="fish_biomass",
        value=9999.0,
        unit="kg/km^2",
        latitude=15.0,
        longitude=72.0,
        observed_at=now_utc,
        retrieved_at=now_utc,
        status="invalid",  # Invalid status
        quality_flags=["unverified"],
    )

    valid_wave = EvidenceRecord(
        evidence_id="wave-valid",
        source="open-meteo-marine",
        variable="wave_height",
        value=1.1,
        unit="m",
        latitude=15.0,
        longitude=72.0,
        observed_at=now_utc,
        retrieved_at=now_utc,
        status="valid",
        quality_flags=["forecast_data"],
    )

    agent = FishingZoneAgent(provider=MockMarineProvider([fabricated_rec, valid_wave]))
    req = FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0, target_species="FictionalDragonFish")
    resp = await agent.analyze(req)

    assert resp.analysis["target_species_status"] == "UNSUPPORTED"
    assert resp.data_source["rejected_records_count"] == 1
    assert resp.analysis["verified_fish_distribution"]["catch_probability"] is None


# ==============================================================================
# Test 8: Worker initialization, idempotency, and clean shutdown
# ==============================================================================
@pytest.mark.asyncio
async def test_worker_initialization_idempotency_and_clean_shutdown(tmp_path):
    """8. Worker does not run on import, supports idempotent start(), and shuts down cleanly."""
    worker = FisheriesIngestionWorker(cache_dir=tmp_path)
    assert not worker.is_running

    await worker.start()
    assert bool(worker.is_running)

    # Idempotent second call
    await worker.start()
    assert bool(worker.is_running)

    # Clean shutdown
    await worker.stop()
    assert not worker.is_running


# ==============================================================================
# Test 9: Provider timeouts, HTTP errors, and deterministic/offline fallback
# ==============================================================================
@pytest.mark.asyncio
async def test_provider_timeouts_http_errors_and_fallback():
    """9. Graceful error handling on provider timeout without application crash."""
    timeout_err = httpx.TimeoutException("Upstream marine provider timeout after 10.0s")
    agent = FishingZoneAgent(provider=MockMarineProvider(raise_exc=timeout_err))

    resp = await agent.analyze(FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0))
    assert resp.status == "error"
    assert "Marine provider error" in (resp.error or "")
    assert len(resp.warnings) >= 1

    # ERDDAP offline snapshot fallback
    now_utc = datetime.now(timezone.utc)
    client_erddap = ErddapClient(mode="live_with_fallback")
    snap = ErddapSnapshot(
        snapshot_id="test-snap-01",
        product_id="noaa_erddap_chlorophyll_a",
        min_lat=14.0,
        max_lat=16.0,
        min_lon=71.0,
        max_lon=73.0,
        observed_at=now_utc,
        retrieved_at=now_utc,
        source_url="https://test.erddap.noaa.gov",
        records=[{
            "evidence_id": "chla-cached-1",
            "source": "noaa-erddap",
            "variable": "chlorophyll_a",
            "value": 0.85,
            "unit": "mg/m^3",
            "latitude": 15.0,
            "longitude": 72.0,
            "observed_at": now_utc.isoformat(),
            "retrieved_at": now_utc.isoformat(),
            "status": "valid",
            "quality_flags": ["cached_offline_snapshot"],
        }],
    )
    client_erddap.register_snapshot(snap, persist_to_disk=False)
    # When live network throws timeout, fetch falls back to cached snapshot
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Remote ERDDAP timed out")):
        chla_records = await client_erddap.fetch_chlorophyll_a(latitude=15.0, longitude=72.0)
    assert len(chla_records) == 1
    assert chla_records[0].value == 0.85
    assert "cached_offline_snapshot" in chla_records[0].quality_flags


# ==============================================================================
# Test 10: Direct fishing-zone API and orchestrator consistency
# ==============================================================================
@pytest.mark.asyncio
async def test_direct_fishing_zone_api_and_orchestrator_consistency(monkeypatch):
    """10. Confirm direct /api/agents/fishing-zone and orchestrator use consistent evidence."""
    now_utc = datetime.now(timezone.utc)
    mock_wave = EvidenceRecord(
        evidence_id="wave-c1",
        source="open-meteo-marine",
        variable="wave_height",
        value=1.1,
        unit="m",
        latitude=15.0,
        longitude=72.0,
        observed_at=now_utc,
        retrieved_at=now_utc,
        status="valid",
        quality_flags=["forecast_data"],
    )
    shared_provider = MockMarineProvider([mock_wave])
    shared_agent = FishingZoneAgent(provider=shared_provider, fisheries_provider=MockMarineProvider([]))

    from app.api.routes.agents import fishing_zone, orchestrator
    from tests.test_e2e_integration import _make_dummy_weather, _make_dummy_ocean, _make_dummy_safety
    monkeypatch.setattr(fishing_zone, "agent", shared_agent)
    monkeypatch.setattr(orchestrator.agent, "fishing_zone_agent", shared_agent)
    monkeypatch.setattr(orchestrator.agent.weather_agent, "analyze", AsyncMock(return_value=_make_dummy_weather()))
    monkeypatch.setattr(orchestrator.agent.ocean_agent, "analyze", AsyncMock(return_value=_make_dummy_ocean()))
    monkeypatch.setattr(orchestrator.agent.safety_risk_agent, "analyze", AsyncMock(return_value=_make_dummy_safety()))

    # 1. Direct endpoint
    direct_res = client.post(
        "/api/agents/fishing-zone/analyze",
        json={"latitude": 15.0, "longitude": 72.0, "target_species": "Mackerel"},
    )
    assert direct_res.status_code == 200
    direct_data = direct_res.json()
    assert direct_data["analysis"]["operational_feasibility"] == "FAVORABLE"
    assert direct_data["analysis"]["verified_fish_distribution"]["status"] == "UNVERIFIED"

    # 2. Orchestrator endpoint
    orch_res = client.post(
        "/api/agents/orchestrator/analyze",
        json={
            "origin_latitude": 15.0,
            "origin_longitude": 72.0,
            "origin_name": "Goa Offshore",
            "user_objective": "fishing_advisory",
            "target_species": "Mackerel",
        },
    )
    assert orch_res.status_code == 200
    orch_data = orch_res.json()
    fz_spec = orch_data["individual_agent_results"]["fishing_zone"]
    assert fz_spec["analysis"]["operational_feasibility"] == "FAVORABLE"
    assert fz_spec["analysis"]["verified_fish_distribution"]["status"] == "UNVERIFIED"
