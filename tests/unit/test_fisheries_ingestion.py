"""Tests for Resilient Fisheries Data Ingestion and Offline Fixture Mode.

Verifies:
1. Successful ingestion using local test fixtures (INCOIS PFZ & NOAA ERDDAP).
2. Handling of invalid, malformed, and empty provider responses.
3. Provider timeout and HTTP 5xx error handling.
4. Retry and recovery behavior under transient network faults.
5. Offline ERDDAP fixture mode: cache hit, cache miss, expired snapshot, and mismatched region.
6. Evidence provenance, timezone validation, and freshness policies.
7. Fishing Zone Agent behavior with resilient ingestion pipeline and INSUFFICIENT_EVIDENCE preservation.
"""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import pytest
import httpx
from unittest.mock import AsyncMock, patch

from app.agents.fishing_zone_agent import FishingZoneAgent
from app.data_sources.erddap_client import ErddapClient, ErddapSnapshot
from app.data_sources.incois_pfz import (
    IncoisPfzBulletinParser,
    IncoisPfzClient,
    point_in_polygon,
)
from app.data_sources.ingestion_worker import (
    FisheriesIngestionWorker,
    get_fisheries_worker,
    set_fisheries_worker,
)
from app.schemas.agent_schemas import FishingZoneAnalyzeRequest
from app.schemas.evidence import EvidenceRecord

FIXTURES_DIR = Path("tests/fixtures")


# ==============================================================================
# 1. Successful Ingestion using Local Test Fixtures
# ==============================================================================

def test_incois_pfz_fixture_ingestion():
    """Verify that a valid INCOIS PFZ GeoJSON fixture parses into valid EvidenceRecords."""
    fixture_path = FIXTURES_DIR / "incois_pfz_sample.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))

    parser = IncoisPfzBulletinParser()
    records = parser.parse_geojson(data, source_url="https://incois.gov.in/test-bulletin")

    assert len(records) > 0
    # Should contain potential_fishing_zone, sea_surface_temperature, and chlorophyll_a records
    variables = {r.variable for r in records}
    assert "potential_fishing_zone" in variables
    assert "sea_surface_temperature" in variables
    assert "chlorophyll_a" in variables

    pfz_rec = next(r for r in records if r.variable == "potential_fishing_zone")
    assert pfz_rec.status == "valid"
    assert pfz_rec.source == "incois-pfz"
    assert "official_government_advisory" in pfz_rec.quality_flags
    assert pfz_rec.metadata["bulletin_id"] == "INCOIS-PFZ-GOA-2026-10-12"
    assert pfz_rec.metadata["sector"] == "Goa Offshore Waters"
    assert pfz_rec.metadata["landing_centre"] == "Malim / Panaji"
    assert pfz_rec.metadata["distance_km"] == 42.0
    assert pfz_rec.observed_at is not None
    assert pfz_rec.observed_at.tzinfo is not None


def test_erddap_chlorophyll_fixture_ingestion():
    """Verify that a NOAA ERDDAP griddap JSON table fixture parses into valid EvidenceRecords."""
    fixture_path = FIXTURES_DIR / "erddap_chla_sample.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))

    client = ErddapClient(mode="live_only")
    records = client.parse_erddap_json_table(
        data,
        variable_name="chlorophyll_a",
        unit="mg/m^3",
        source_url="https://coastwatch.pfeg.noaa.gov/erddap/test",
    )

    assert len(records) == 4
    for r in records:
        assert r.variable == "chlorophyll_a"
        assert r.unit == "mg/m^3"
        assert 0.5 <= r.value <= 1.0
        assert r.latitude in (15.0, 15.05)
        assert r.longitude in (72.0, 72.05)
        assert r.status == "valid"
        assert "satellite_remote_sensing" in r.quality_flags
        assert r.observed_at is not None
        assert r.observed_at.tzinfo is not None


# ==============================================================================
# 2. Invalid, Malformed, and Empty Responses
# ==============================================================================

def test_incois_malformed_json_raises_value_error():
    """Malformed non-JSON string must raise ValueError."""
    parser = IncoisPfzBulletinParser()
    with pytest.raises(ValueError, match="Malformed JSON"):
        parser.parse_geojson("NOT_VALID_JSON{")


def test_incois_non_feature_collection_raises_value_error():
    """Invalid GeoJSON types must raise ValueError."""
    parser = IncoisPfzBulletinParser()
    with pytest.raises(ValueError, match="Expected GeoJSON FeatureCollection"):
        parser.parse_geojson({"type": "InvalidType", "data": []})


def test_incois_empty_features_returns_empty_list():
    """Empty GeoJSON FeatureCollection returns an empty list without crashing."""
    parser = IncoisPfzBulletinParser()
    records = parser.parse_geojson({"type": "FeatureCollection", "features": []})
    assert records == []


def test_incois_skips_malformed_feature_and_keeps_valid():
    """Partial failure: corrupted feature is skipped while valid feature is preserved."""
    parser = IncoisPfzBulletinParser()
    payload = {
      "type": "FeatureCollection",
      "features": [
        "not-a-dict",  # Corrupted entry
        {
          "type": "Feature",
          "properties": {"bulletin_id": "b-valid"},
          "geometry": {"type": "Point", "coordinates": [72.0, 15.0]}
        },
        {
          "type": "Feature",
          "properties": {"bulletin_id": "b-out-of-bounds"},
          "geometry": {"type": "Point", "coordinates": [250.0, 15.0]}  # Lon > 180 invalid
        }
      ]
    }
    records = parser.parse_geojson(payload)
    assert len(records) == 1
    assert records[0].source_record_id == "b-valid"
    assert records[0].latitude == 15.0
    assert records[0].longitude == 72.0


def test_incois_deduplicates_identical_features():
    """Duplicate features in bulletin are deduplicated cleanly."""
    parser = IncoisPfzBulletinParser()
    feature = {
        "type": "Feature",
        "properties": {"bulletin_id": "b-dup", "sector": "Goa"},
        "geometry": {"type": "Point", "coordinates": [72.0, 15.0]},
    }
    payload = {
        "type": "FeatureCollection",
        "features": [feature, feature, feature],
    }
    records = parser.parse_geojson(payload)
    assert len(records) == 1


# ==============================================================================
# 3. Provider Timeout and HTTP 5xx Error Handling
# ==============================================================================

@pytest.mark.asyncio
async def test_incois_client_http_502_error():
    """Simulated upstream HTTP 502 error raises HTTPStatusError after retries."""
    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(502, text="Proxy Error")
    )
    client = IncoisPfzClient(base_url="https://incois.gov.in/api/pfz", max_retries=1)

    async with httpx.AsyncClient(transport=mock_transport) as session:
        with pytest.raises(httpx.HTTPStatusError):
            await client.fetch_bulletin(client=session)


@pytest.mark.asyncio
async def test_erddap_client_timeout_handling(tmp_path):
    """Simulated timeout on live ERDDAP fetch triggers fallback without unhandled crash."""
    def timeout_handler(req):
        raise httpx.ReadTimeout("Connection timed out after 10s")

    mock_transport = httpx.MockTransport(timeout_handler)
    erddap = ErddapClient(
        cache_dir=tmp_path,
        mode="live_only",
        timeout_seconds=0.1,
        max_retries=1,
    )

    async with httpx.AsyncClient(transport=mock_transport) as session:
        records = await erddap.fetch_chlorophyll_a(15.0, 72.0, client=session)
        assert records == []


# ==============================================================================
# 4. Retry and Recovery Behavior Under Transient Faults
# ==============================================================================

@pytest.mark.asyncio
async def test_erddap_recovers_on_retry(tmp_path):
    """Client retries on transient 503 error and successfully parses response on attempt 2."""
    fixture_path = FIXTURES_DIR / "erddap_chla_sample.json"
    success_json = json.loads(fixture_path.read_text(encoding="utf-8"))

    attempt_count = 0

    def mock_handler(req):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            return httpx.Response(503, text="Service Unavailable")
        return httpx.Response(200, json=success_json)

    mock_transport = httpx.MockTransport(mock_handler)
    erddap = ErddapClient(
        cache_dir=tmp_path,
        mode="live_only",
        max_retries=2,
    )

    async with httpx.AsyncClient(transport=mock_transport) as session:
        records = await erddap.fetch_chlorophyll_a(15.0, 72.0, client=session)
        assert attempt_count == 2
        assert len(records) == 4
        assert records[0].variable == "chlorophyll_a"


# ==============================================================================
# 5. Offline ERDDAP Fixture Mode: Cache Hit, Cache Miss, Expired, Mismatched
# ==============================================================================

def test_erddap_cache_hit_matching_region(tmp_path):
    """Cache hit: Valid snapshot enclosing requested coordinates is returned with offline indicators."""
    now_utc = datetime.now(timezone.utc)
    erddap = ErddapClient(cache_dir=tmp_path, mode="fixture_only")

    # Seed snapshot for Goa region: lat [14.8, 15.5], lon [71.8, 72.5]
    snapshot = ErddapSnapshot(
        snapshot_id="snap-goa-001",
        product_id="noaa_erddap_chlorophyll_a",
        min_lat=14.8,
        max_lat=15.5,
        min_lon=71.8,
        max_lon=72.5,
        observed_at=now_utc - timedelta(hours=2),
        retrieved_at=now_utc - timedelta(hours=1),
        source_url="https://coastwatch.pfeg.noaa.gov/erddap/test",
        records=[
            {
                "evidence_id": "seed-chla-1",
                "source": "noaa-erddap",
                "variable": "chlorophyll_a",
                "value": 0.58,
                "unit": "mg/m^3",
                "latitude": 15.0,
                "longitude": 72.0,
                "observed_at": (now_utc - timedelta(hours=2)).isoformat(),
                "retrieved_at": (now_utc - timedelta(hours=1)).isoformat(),
                "status": "valid",
                "quality_flags": ["satellite_remote_sensing"],
            }
        ],
    )
    erddap.register_snapshot(snapshot)

    # Query coordinate (15.0, 72.0) falls inside bounding box
    matched_records = erddap._serve_snapshot_records(
        "noaa_erddap_chlorophyll_a",
        latitude=15.0,
        longitude=72.0,
        now_utc=now_utc,
    )

    assert len(matched_records) == 1
    rec = matched_records[0]
    assert rec.variable == "chlorophyll_a"
    assert rec.value == 0.58
    assert "cached_offline_snapshot" in rec.quality_flags
    assert "offline_fixture" in rec.quality_flags
    assert rec.metadata["is_cached_snapshot"] is True
    assert rec.metadata["snapshot_id"] == "snap-goa-001"
    assert rec.metadata["snapshot_age_seconds"] >= 3600.0


def test_erddap_cache_mismatched_region_returns_empty(tmp_path):
    """Mismatched region: Query outside snapshot bounds must return empty, never false location attribution."""
    now_utc = datetime.now(timezone.utc)
    erddap = ErddapClient(cache_dir=tmp_path, mode="fixture_only")

    # Snapshot is bounded to Goa: lat [14.8, 15.5], lon [71.8, 72.5]
    snapshot = ErddapSnapshot(
        snapshot_id="snap-goa-001",
        product_id="noaa_erddap_chlorophyll_a",
        min_lat=14.8,
        max_lat=15.5,
        min_lon=71.8,
        max_lon=72.5,
        observed_at=now_utc - timedelta(hours=2),
        retrieved_at=now_utc - timedelta(hours=1),
        source_url="https://coastwatch.pfeg.noaa.gov/erddap/test",
        records=[],
    )
    erddap.register_snapshot(snapshot)

    # Query Bay of Bengal / Chennai coordinates: (13.0, 80.2)
    matched, diag = erddap.find_matching_snapshot(
        "noaa_erddap_chlorophyll_a",
        latitude=13.0,
        longitude=80.2,
        now=now_utc,
    )
    assert matched is None
    assert diag["product_matches"] == 1
    assert diag["region_matches"] == 0


def test_erddap_cache_miss_unregistered_product(tmp_path):
    """Cache miss: Querying a product with no snapshots returns None."""
    erddap = ErddapClient(cache_dir=tmp_path, mode="fixture_only")
    matched, diag = erddap.find_matching_snapshot("unregistered_product", 15.0, 72.0)
    assert matched is None
    assert diag["product_matches"] == 0


def test_erddap_expired_snapshot_marked_stale(tmp_path):
    """Expired snapshot older than 24h is marked with status='stale'."""
    now_utc = datetime.now(timezone.utc)
    erddap = ErddapClient(cache_dir=tmp_path, mode="fixture_only")

    # Snapshot retrieved 48 hours ago
    snapshot = ErddapSnapshot(
        snapshot_id="snap-old",
        product_id="noaa_erddap_chlorophyll_a",
        min_lat=14.0,
        max_lat=16.0,
        min_lon=71.0,
        max_lon=73.0,
        observed_at=now_utc - timedelta(hours=48),
        retrieved_at=now_utc - timedelta(hours=48),
        source_url="https://coastwatch.pfeg.noaa.gov/erddap/test",
        records=[
            {
                "evidence_id": "seed-old",
                "source": "noaa-erddap",
                "variable": "chlorophyll_a",
                "value": 0.45,
                "unit": "mg/m^3",
                "latitude": 15.0,
                "longitude": 72.0,
                "observed_at": (now_utc - timedelta(hours=48)).isoformat(),
                "retrieved_at": (now_utc - timedelta(hours=48)).isoformat(),
                "status": "valid",
                "quality_flags": ["satellite_remote_sensing"],
            }
        ],
    )
    erddap.register_snapshot(snapshot)

    records = erddap._serve_snapshot_records(
        "noaa_erddap_chlorophyll_a",
        15.0,
        72.0,
        now_utc,
    )
    assert len(records) == 1
    assert records[0].status == "stale"


# ==============================================================================
# 6. Spatial Polygon Matcher Tests
# ==============================================================================

def test_point_in_polygon_ray_casting():
    """Verify ray-casting algorithm for spatial containment."""
    # Unit box from (0,0) to (10,10)
    box = [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]
    assert point_in_polygon(5.0, 5.0, box) is True
    assert point_in_polygon(15.0, 5.0, box) is False
    assert point_in_polygon(-1.0, 5.0, box) is False
    assert point_in_polygon(5.0, 15.0, box) is False


# ==============================================================================
# 7. Asynchronous Ingestion Worker Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_ingestion_worker_incois_and_erddap(tmp_path):
    """Test non-blocking IngestionWorker combining INCOIS bulletins and ERDDAP snapshots."""
    now_utc = datetime.now(timezone.utc)
    incois_fixture = json.loads((FIXTURES_DIR / "incois_pfz_sample.json").read_text(encoding="utf-8"))

    erddap = ErddapClient(cache_dir=tmp_path, mode="fixture_only")
    erddap.register_snapshot(
        ErddapSnapshot(
            snapshot_id="snap-chla-worker",
            product_id="noaa_erddap_chlorophyll_a",
            min_lat=14.5,
            max_lat=15.8,
            min_lon=71.5,
            max_lon=73.5,
            observed_at=now_utc - timedelta(hours=2),
            retrieved_at=now_utc - timedelta(hours=1),
            source_url="https://coastwatch.pfeg.noaa.gov/erddap/test",
            records=[
                {
                    "evidence_id": "rec-chla-worker",
                    "source": "noaa-erddap",
                    "variable": "chlorophyll_a",
                    "value": 0.72,
                    "unit": "mg/m^3",
                    "latitude": 15.3,
                    "longitude": 73.0,
                    "observed_at": (now_utc - timedelta(hours=2)).isoformat(),
                    "retrieved_at": (now_utc - timedelta(hours=1)).isoformat(),
                    "status": "valid",
                    "quality_flags": ["satellite_remote_sensing"],
                }
            ],
        )
    )

    worker = FisheriesIngestionWorker(
        erddap_client=erddap,
        cache_dir=tmp_path,
    )

    # Ingest INCOIS GeoJSON bulletin
    await worker.ingest_incois_geojson(incois_fixture)

    status = worker.get_provider_status()
    assert status["in_memory_records_count"] > 0
    assert status["cached_snapshots_count"] == 1

    # Fetch evidence for position inside polygon (15.4°N, 73.1°E)
    evidence = await worker.fetch(latitude=15.4, longitude=73.1)
    assert len(evidence) > 0
    vars_found = {e.variable for e in evidence}
    assert "potential_fishing_zone" in vars_found
    assert "chlorophyll_a" in vars_found


# ==============================================================================
# 8. Fishing Zone Agent Integration & INSUFFICIENT_EVIDENCE Preservation
# ==============================================================================

@pytest.mark.asyncio
async def test_fishing_zone_agent_with_resilient_fisheries_provider():
    """Agent incorporates resilient fisheries provider records while keeping evidence separation."""
    now_utc = datetime.now(timezone.utc)
    mock_wave_provider = AsyncMock()
    mock_wave_provider.provider_name = "open-meteo-marine"
    mock_wave_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="fz-wave-1",
            source="open-meteo-marine",
            source_record_id="wave-1",
            variable="wave_height",
            value=0.95,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        )
    ]

    mock_fisheries_provider = AsyncMock()
    mock_fisheries_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="snap-chla-1",
            source="noaa-erddap-cached-fixture",
            source_record_id="chla-1",
            variable="chlorophyll_a",
            value=0.74,
            unit="mg/m^3",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
            quality_flags=["cached_offline_snapshot", "offline_fixture"],
            metadata={"is_cached_snapshot": True, "snapshot_age_seconds": 1200.0},
        )
    ]

    agent = FishingZoneAgent(
        provider=mock_wave_provider,
        fisheries_provider=mock_fisheries_provider,
    )
    req = FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0, target_species="Mackerel")
    resp = await agent.analyze(req)

    # Physical operability evaluates wave conditions
    assert resp.analysis["operational_feasibility"] == "FAVORABLE"
    assert resp.observations["chlorophyll_a_mg_m3"] == 0.74

    # Offline snapshot warning is clearly present
    assert any("Offline cached fisheries/satellite snapshot in use" in w for w in resp.warnings)

    # When biomass telemetry is missing, status remains INSUFFICIENT_EVIDENCE
    assert resp.status == "insufficient_evidence"
    assert resp.analysis["zone_suitability"] == "INSUFFICIENT_EVIDENCE"


@pytest.mark.asyncio
async def test_fishing_zone_agent_empty_fisheries_provider_preserves_insufficient_evidence():
    """When fisheries provider returns no data, agent preserves INSUFFICIENT_EVIDENCE strictly."""
    now_utc = datetime.now(timezone.utc)
    mock_wave_provider = AsyncMock()
    mock_wave_provider.provider_name = "open-meteo-marine"
    mock_wave_provider.fetch.return_value = [
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
        )
    ]

    mock_fisheries_provider = AsyncMock()
    mock_fisheries_provider.fetch.return_value = []  # Empty / unavailable

    agent = FishingZoneAgent(
        provider=mock_wave_provider,
        fisheries_provider=mock_fisheries_provider,
    )
    req = FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0)
    resp = await agent.analyze(req)

    assert resp.status == "insufficient_evidence"
    assert resp.analysis["zone_suitability"] == "INSUFFICIENT_EVIDENCE"
    assert resp.analysis["verified_fish_distribution"]["status"] == "UNVERIFIED"
    assert resp.analysis["scoring"]["suitability_score"] is None


# ==============================================================================
# 8. Production-Readiness Lifecycle & Mode Metadata Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_fisheries_worker_start_stop_lifecycle(tmp_path):
    """Worker start() spawns background task, prevents duplicates, and stop() cleanly cancels it."""
    worker = FisheriesIngestionWorker(cache_dir=tmp_path)
    assert not worker.is_running

    await worker.start()
    assert worker.is_running

    # Idempotent: starting again does not spawn a second task
    first_task = worker._background_task
    await worker.start()
    assert worker._background_task is first_task
    assert worker.is_running

    # Clean shutdown
    await worker.stop()
    assert not worker.is_running
    assert worker._background_task is None


def test_fisheries_worker_singleton_getters():
    """get_fisheries_worker returns consistent singleton and set_fisheries_worker allows reset."""
    w1 = get_fisheries_worker()
    w2 = get_fisheries_worker()
    assert w1 is w2

    custom_w = FisheriesIngestionWorker()
    set_fisheries_worker(custom_w)
    assert get_fisheries_worker() is custom_w

    # Restore default
    set_fisheries_worker(None)
    assert get_fisheries_worker() is not custom_w


@pytest.mark.asyncio
async def test_fishing_zone_agent_distinguishes_live_vs_offline_cached_modes():
    """FishingZoneAgent clearly sets active_data_mode and is_offline_fixture flags in data_source."""
    now_utc = datetime.now(timezone.utc)
    mock_wave_provider = AsyncMock()
    mock_wave_provider.provider_name = "open-meteo-marine"
    mock_wave_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="wave-1",
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

    # 1. Without offline snapshot: active_data_mode == "live"
    agent_live = FishingZoneAgent(provider=mock_wave_provider)
    resp_live = await agent_live.analyze(FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0))
    assert resp_live.data_source["active_data_mode"] == "live"
    assert resp_live.data_source["is_offline_fixture"] is False

    # 2. With offline cached snapshot: active_data_mode == "offline_cached"
    mock_fisheries = AsyncMock()
    mock_fisheries.fetch.return_value = [
        EvidenceRecord(
            evidence_id="chla-snap-1",
            source="noaa-erddap-cached-fixture",
            source_record_id="row-1",
            variable="chlorophyll_a",
            value=0.65,
            unit="mg/m^3",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
            quality_flags=["cached_offline_snapshot", "offline_fixture"],
        )
    ]
    agent_cached = FishingZoneAgent(provider=mock_wave_provider, fisheries_provider=mock_fisheries)
    resp_cached = await agent_cached.analyze(FishingZoneAnalyzeRequest(latitude=15.0, longitude=72.0))
    assert resp_cached.data_source["active_data_mode"] == "offline_cached"
    assert resp_cached.data_source["is_offline_fixture"] is True

