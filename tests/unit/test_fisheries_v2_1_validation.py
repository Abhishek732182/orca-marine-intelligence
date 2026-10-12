"""Deterministic Validation Tests for ORCA Fisheries Intelligence v2.1.

Milestone 1: Real-World Fisheries Data Validation.
Covers all required scenarios from prompt:
1. Fresh live observation.
2. Recently retrieved but old cached observation.
3. Stale satellite observation older than 24 hours.
4. Missing or invalid observed_at never classified as fresh.
5. Cloud-masked null chlorophyll values.
6. Fixture evidence versus live INCOIS evidence.
7. Provider unavailable WITH a cached snapshot (fallback).
8. Provider unavailable WITHOUT a cached snapshot (empty diagnostic result).
9. All five source-state classifications (LIVE_VALIDATED, CACHED_OBSERVATION, STALE_OBSERVATION, EMPTY_RESULT, UNAVAILABLE_PROVIDER).
10. Stale records retained for diagnostics but excluded from current scoring.
"""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch
import httpx
import pytest

from app.agents.fishing_zone_agent import FishingZoneAgent
from app.data_sources.base import MarineDataProvider
from app.data_sources.erddap_client import ErddapClient, ErddapSnapshot
from app.data_sources.incois_pfz import IncoisPfzBulletinParser, IncoisPfzClient
from app.schemas.agent_schemas import FishingZoneAnalyzeRequest
from app.schemas.evidence import EvidenceRecord

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
if not FIXTURES_DIR.exists():
    FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures"


class MockEvidenceProvider(MarineDataProvider):
    """Deterministic provider supplying predefined evidence records."""

    def __init__(self, records: list[EvidenceRecord] | None = None, raise_exc: Exception | None = None) -> None:
        self.records = records or []
        self.raise_exc = raise_exc

    @property
    def provider_name(self) -> str:
        return "mock-evidence-provider"

    async def fetch(self, *, latitude: float, longitude: float, observed_at: str | None = None) -> list[EvidenceRecord]:
        if self.raise_exc:
            raise self.raise_exc
        return list(self.records)


# ==============================================================================
# Test 1: Fresh live observation
# ==============================================================================
@pytest.mark.asyncio
async def test_fresh_live_observation():
    """1. Valid fresh observation within policy window is classified as LIVE_VALIDATED."""
    now_utc = datetime.now(timezone.utc)
    fresh_time = now_utc - timedelta(hours=1)

    live_wave = EvidenceRecord(
        evidence_id="wave-fresh-1",
        source="open-meteo-marine",
        variable="wave_height",
        value=1.1,
        unit="m",
        latitude=15.0,
        longitude=72.0,
        observed_at=fresh_time,
        retrieved_at=now_utc,
        status="valid",
        quality_flags=[],
    )

    live_sst = EvidenceRecord(
        evidence_id="sst-fresh-1",
        source="open-meteo-marine",
        variable="sea_surface_temperature",
        value=28.5,
        unit="°C",
        latitude=15.0,
        longitude=72.0,
        observed_at=fresh_time,
        retrieved_at=now_utc,
        status="valid",
        quality_flags=[],
    )

    agent = FishingZoneAgent(provider=MockEvidenceProvider([live_wave, live_sst]))
    resp = await agent.analyze(FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0))

    assert resp.data_source["active_data_mode"] == "live"
    assert resp.data_source["is_offline_fixture"] is False
    prov = resp.observations["evidence_provenance"]
    assert prov["wave_height"]["provenance_status"] == "LIVE_VALIDATED"
    assert prov["sea_surface_temperature"]["provenance_status"] == "LIVE_VALIDATED"
    assert resp.data_source["provider_states"]["wave_height"] == "LIVE_VALIDATED"
    assert resp.data_source["provider_states"]["sea_surface_temperature"] == "LIVE_VALIDATED"


# ==============================================================================
# Test 2: Recently retrieved but old cached observation
# ==============================================================================
@pytest.mark.asyncio
async def test_recently_retrieved_old_cached_observation():
    """2. Snapshot retrieved recently but containing older data is marked stale and CACHED_OBSERVATION."""
    now_utc = datetime.now(timezone.utc)
    original_obs_time = now_utc - timedelta(days=5)  # 5-day old satellite pass
    retrieval_time = now_utc  # retrieved right now

    client = ErddapClient(mode="fixture_only")
    snapshot = ErddapSnapshot(
        snapshot_id="test-snap-recent-fetch-old-data",
        product_id="noaa_erddap_chlorophyll_a",
        min_lat=14.0,
        max_lat=16.0,
        min_lon=71.0,
        max_lon=73.0,
        observed_at=original_obs_time,
        retrieved_at=retrieval_time,
        source_url="https://coastwatch.noaa.gov/test",
        records=[
            {
                "evidence_id": "chla-raw-1",
                "source": "noaa-erddap",
                "source_record_id": "r-1",
                "variable": "chlorophyll_a",
                "value": 0.85,
                "unit": "mg/m^3",
                "latitude": 15.0,
                "longitude": 72.0,
                "observed_at": original_obs_time.isoformat(),
                "retrieved_at": retrieval_time.isoformat(),
                "status": "valid",
                "quality_flags": ["satellite_remote_sensing"],
                "metadata": {},
            }
        ],
    )
    client.register_snapshot(snapshot, persist_to_disk=False)

    records = await client.fetch_chlorophyll_a(latitude=15.0, longitude=72.0, now=now_utc)
    assert len(records) == 1
    served_rec = records[0]

    # Timestamp preservation
    assert served_rec.observed_at == original_obs_time
    assert served_rec.retrieved_at == now_utc
    assert served_rec.observed_at != served_rec.retrieved_at
    # Must remain stale due to observation age, despite recent retrieval
    assert served_rec.status == "stale"
    assert "cached_offline_snapshot" in served_rec.quality_flags


# ==============================================================================
# Test 3: Stale satellite observation older than 24 hours
# ==============================================================================
@pytest.mark.asyncio
async def test_stale_satellite_observation_older_than_24h():
    """3. Satellite observations older than 24h are flagged stale and excluded from scoring."""
    now_utc = datetime.now(timezone.utc)
    stale_satellite_time = now_utc - timedelta(hours=36)

    fresh_wave = EvidenceRecord(
        evidence_id="wave-fresh-1",
        source="open-meteo-marine",
        variable="wave_height",
        value=1.1,
        unit="m",
        latitude=15.0,
        longitude=72.0,
        observed_at=now_utc - timedelta(hours=1),
        retrieved_at=now_utc,
        status="valid",
        quality_flags=["forecast_data"],
    )

    stale_chla = EvidenceRecord(
        evidence_id="chla-stale-1",
        source="noaa-erddap",
        variable="chlorophyll_a",
        value=0.75,
        unit="mg/m^3",
        latitude=15.0,
        longitude=72.0,
        observed_at=stale_satellite_time,
        retrieved_at=now_utc,
        status="valid",
        quality_flags=["satellite_remote_sensing"],
    )

    agent = FishingZoneAgent(provider=MockEvidenceProvider([fresh_wave, stale_chla]))
    resp = await agent.analyze(FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0))

    # Excluded from current biological scoring
    assert resp.observations["chlorophyll_a_mg_m3"] is None
    assert resp.analysis["environmental_habitat_indicators"]["chlorophyll_a_mg_m3"] is None
    assert any("stale" in r["reason"].lower() for r in resp.data_source["rejected_records"])
    # Rejected record remains None in evidence_provenance
    assert resp.observations["evidence_provenance"]["chlorophyll_a"] is None
    # Provider states reflects STALE_OBSERVATION
    assert resp.data_source["provider_states"]["chlorophyll_a"] == "STALE_OBSERVATION"


# ==============================================================================
# Test 4: Missing or invalid observed_at never classified as fresh
# ==============================================================================
@pytest.mark.asyncio
async def test_missing_or_invalid_observed_at_never_classified_as_fresh():
    """4. If observation timestamp is absent or invalid, record must not be classified as fresh."""
    now_utc = datetime.now(timezone.utc)
    client = ErddapClient(mode="fixture_only")

    # Snapshot with None for observed_at
    snapshot = ErddapSnapshot(
        snapshot_id="test-snap-no-observed-at",
        product_id="noaa_erddap_chlorophyll_a",
        min_lat=14.0,
        max_lat=16.0,
        min_lon=71.0,
        max_lon=73.0,
        observed_at=now_utc - timedelta(hours=1),  # snapshot header has time
        retrieved_at=now_utc,
        source_url="https://coastwatch.noaa.gov/test",
        records=[
            {
                "evidence_id": "chla-none-time",
                "source": "noaa-erddap",
                "source_record_id": "r-none",
                "variable": "chlorophyll_a",
                "value": 0.85,
                "unit": "mg/m^3",
                "latitude": 15.0,
                "longitude": 72.0,
                "observed_at": None,  # Absent observation timestamp
                "retrieved_at": now_utc.isoformat(),
                "status": "valid",
                "quality_flags": ["satellite_remote_sensing"],
                "metadata": {},
            }
        ],
    )
    # Mutate observed_at of snapshot to None to test edge case
    snapshot.observed_at = None
    client.register_snapshot(snapshot, persist_to_disk=False)

    records = await client.fetch_chlorophyll_a(latitude=15.0, longitude=72.0, now=now_utc)
    assert len(records) == 1
    # Must be marked stale because observation timestamp is absent
    assert records[0].status == "stale"


# ==============================================================================
# Test 5: Cloud-masked null chlorophyll values
# ==============================================================================
def test_cloud_masked_null_chlorophyll_values():
    """5. Cloud-masked satellite optical pixels (None values) produce zero records without fabrication."""
    client = ErddapClient(mode="live_only")

    cloud_masked_response = {
        "table": {
            "columnNames": ["time", "altitude", "latitude", "longitude", "chlor_a"],
            "columnUnits": ["UTC", "m", "degrees_north", "degrees_east", "mg m-3"],
            "columnTypes": ["String", "float", "float", "float", "float"],
            "rows": [
                ["2026-10-02T12:00:00Z", 0.0, 15.00, 71.95, None],
                ["2026-10-02T12:00:00Z", 0.0, 15.00, 72.00, None],
                ["2026-10-02T12:00:00Z", 0.0, 15.05, 71.95, None],
                ["2026-10-02T12:00:00Z", 0.0, 15.05, 72.00, None],
            ],
        }
    }

    records = client.parse_erddap_json_table(
        cloud_masked_response,
        variable_name="chlorophyll_a",
        unit="mg/m^3",
        source_url="https://coastwatch.noaa.gov/erddap/griddap/noaacwNPPVIIRSSQchlaDaily.json",
    )
    assert len(records) == 0


# ==============================================================================
# Test 6: Fixture evidence versus live INCOIS evidence
# ==============================================================================
def test_fixture_evidence_vs_live_incois_evidence():
    """6. Distinguish offline fixture parsing from live authorized feed."""
    fixture_path = FIXTURES_DIR / "incois_pfz_sample.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    parser = IncoisPfzBulletinParser()

    # Fixture parsing must set offline_fixture flag and metadata
    fixture_records = parser.parse_geojson(data, source_url="tests/fixtures/incois_pfz_sample.json", is_fixture=True)
    assert len(fixture_records) > 0
    for r in fixture_records:
        assert "offline_fixture" in r.quality_flags
        assert r.metadata["is_offline_fixture"] is True

    # Hypothetical live response does not tag offline_fixture
    live_records = parser.parse_geojson(data, source_url="https://incois.gov.in/portal/live", is_fixture=False)
    assert len(live_records) > 0
    for r in live_records:
        assert "offline_fixture" not in r.quality_flags
        assert r.metadata["is_offline_fixture"] is False


# ==============================================================================
# Test 7: Provider unavailable WITH a cached snapshot
# ==============================================================================
@pytest.mark.asyncio
async def test_provider_unavailable_with_cached_snapshot():
    """7. Upstream HTTP failure safely falls back to registered cached snapshot."""
    client = ErddapClient(mode="live_with_fallback", max_retries=1, timeout_seconds=1.0)
    now_utc = datetime.now(timezone.utc)

    cached_snap = ErddapSnapshot(
        snapshot_id="snap-avail-1",
        product_id="noaa_erddap_chlorophyll_a",
        min_lat=14.5,
        max_lat=15.5,
        min_lon=71.5,
        max_lon=72.5,
        observed_at=now_utc - timedelta(hours=2),
        retrieved_at=now_utc - timedelta(hours=2),
        source_url="https://coastwatch.noaa.gov/offline_test",
        records=[
            {
                "evidence_id": "chla-cached-fb",
                "source": "noaa-erddap",
                "source_record_id": "r-0",
                "variable": "chlorophyll_a",
                "value": 0.68,
                "unit": "mg/m^3",
                "latitude": 15.0,
                "longitude": 72.0,
                "observed_at": (now_utc - timedelta(hours=2)).isoformat(),
                "retrieved_at": (now_utc - timedelta(hours=2)).isoformat(),
                "status": "valid",
                "quality_flags": ["satellite_remote_sensing"],
                "metadata": {},
            }
        ],
    )
    client.register_snapshot(cached_snap, persist_to_disk=False)

    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectTimeout("Upstream offline")):
        records = await client.fetch_chlorophyll_a(latitude=15.0, longitude=72.0)

    assert len(records) == 1
    assert records[0].value == 0.68
    assert "cached_offline_snapshot" in records[0].quality_flags


# ==============================================================================
# Test 8: Provider unavailable WITHOUT a cached snapshot
# ==============================================================================
@pytest.mark.asyncio
async def test_provider_unavailable_without_cached_snapshot():
    """8. Upstream HTTP failure without cache hit returns empty list cleanly without crash."""
    client = ErddapClient(mode="live_with_fallback", max_retries=1, timeout_seconds=0.1)

    req = httpx.Request("GET", "https://coastwatch.noaa.gov/erddap")
    resp = httpx.Response(500, request=req)
    with patch("httpx.AsyncClient.get", side_effect=httpx.HTTPStatusError("500 Server Error", request=req, response=resp)):
        records = await client.fetch_chlorophyll_a(latitude=15.0, longitude=72.0)

    assert records == []


# ==============================================================================
# Test 9: All five source-state classifications
# ==============================================================================
@pytest.mark.asyncio
async def test_all_five_source_state_classifications():
    """9. Verify all 5 states: LIVE_VALIDATED, CACHED_OBSERVATION, STALE_OBSERVATION, EMPTY_RESULT, UNAVAILABLE_PROVIDER."""
    now_utc = datetime.now(timezone.utc)

    # 1. LIVE_VALIDATED
    live_wave = EvidenceRecord(
        evidence_id="w-live",
        source="open-meteo-marine",
        variable="wave_height",
        value=1.0,
        unit="m",
        latitude=15.0,
        longitude=72.0,
        observed_at=now_utc - timedelta(hours=1),
        retrieved_at=now_utc,
        status="valid",
        quality_flags=[],
    )

    # 2. CACHED_OBSERVATION
    cached_sst = EvidenceRecord(
        evidence_id="sst-cached",
        source="open-meteo-marine",
        variable="sea_surface_temperature",
        value=28.0,
        unit="°C",
        latitude=15.0,
        longitude=72.0,
        observed_at=now_utc - timedelta(hours=1),
        retrieved_at=now_utc,
        status="valid",
        quality_flags=["cached_offline_snapshot"],
    )

    # 3. STALE_OBSERVATION
    stale_chla = EvidenceRecord(
        evidence_id="chla-stale",
        source="noaa-erddap",
        variable="chlorophyll_a",
        value=0.6,
        unit="mg/m^3",
        latitude=15.0,
        longitude=72.0,
        observed_at=now_utc - timedelta(days=4),
        retrieved_at=now_utc,
        status="valid",
        quality_flags=[],
    )

    agent = FishingZoneAgent(
        provider=MockEvidenceProvider([live_wave, cached_sst, stale_chla]),
        fisheries_provider=None,  # Direct biomass provider unavailable
    )
    resp = await agent.analyze(FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0))

    states = resp.data_source["provider_states"]
    assert states["wave_height"] == "LIVE_VALIDATED"
    assert states["sea_surface_temperature"] == "CACHED_OBSERVATION"
    assert states["chlorophyll_a"] == "STALE_OBSERVATION"
    assert states["fish_biomass"] == "UNAVAILABLE_PROVIDER"

    # Also verify EMPTY_RESULT when provider is present but returns zero records
    agent_empty = FishingZoneAgent(
        provider=MockEvidenceProvider([live_wave]),
        fisheries_provider=MockEvidenceProvider([]),
    )
    resp_empty = await agent_empty.analyze(FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0))
    assert resp_empty.data_source["provider_states"]["chlorophyll_a"] == "EMPTY_RESULT"
    assert resp_empty.data_source["provider_states"]["fish_biomass"] == "EMPTY_RESULT"


# ==============================================================================
# Test 10: Stale records retained for diagnostics but excluded from current scoring
# ==============================================================================
@pytest.mark.asyncio
async def test_stale_records_retained_for_diagnostics_excluded_from_scoring():
    """10. Rejected stale records appear in rejected_records for auditing but never influence suitability score."""
    now_utc = datetime.now(timezone.utc)

    fresh_wave = EvidenceRecord(
        evidence_id="w-1",
        source="open-meteo-marine",
        variable="wave_height",
        value=1.0,
        unit="m",
        latitude=15.0,
        longitude=72.0,
        observed_at=now_utc - timedelta(hours=1),
        retrieved_at=now_utc,
        status="valid",
        quality_flags=[],
    )

    stale_sst = EvidenceRecord(
        evidence_id="sst-stale-diag",
        source="open-meteo-marine",
        variable="sea_surface_temperature",
        value=28.0,
        unit="°C",
        latitude=15.0,
        longitude=72.0,
        observed_at=now_utc - timedelta(hours=12),  # Stale (>6h)
        retrieved_at=now_utc,
        status="valid",
        quality_flags=[],
    )

    agent = FishingZoneAgent(provider=MockEvidenceProvider([fresh_wave, stale_sst]))
    resp = await agent.analyze(FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0, target_species="Mackerel"))

    # Diagnostically recorded
    assert resp.data_source["rejected_records_count"] == 1
    rejected = resp.data_source["rejected_records"][0]
    assert rejected["evidence_id"] == "sst-stale-diag"
    assert "stale" in rejected["reason"].lower()

    # Excluded from scoring
    assert resp.analysis["environmental_habitat_indicators"]["sea_surface_temperature_c"] is None
    assert resp.analysis["scoring"]["suitability_score"] is None
