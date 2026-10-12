"""Deterministic Unit Tests for ORCA Fisheries v2.3 Phase 1: Data Readiness & Reproducibility.

Covers:
1. Station reproducibility manifest schema, station count, and coordinate tracking.
2. Chlorophyll null/cloud-mask rejection (never inferring usable coverage from HTTP 200).
3. Observation staleness evaluation (10-day-old pass retrieved recently is stale).
4. Spatial coverage mismatch filtering (> 50 km threshold).
5. Timestamp preservation and quality flags integrity.
6. Provenance category partitioning (barring fixture & stale data from baseline).
7. Genuine fisheries catch records absence (honestly reporting 0.0% and not_evaluable).
8. End-to-end reproducibility manifest evaluation.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from app.evaluation.fisheries_benchmark import (
    FisheriesBenchmarkEvaluator,
    load_benchmark_dataset,
    load_reproducibility_manifest,
)
from app.schemas.evidence import EvidenceRecord

REFERENCE_TIME = datetime(2026, 10, 12, 4, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def evaluator():
    return FisheriesBenchmarkEvaluator(
        reference_time=REFERENCE_TIME,
        clock_skew_tolerance_seconds=300.0,
        spatial_mismatch_threshold_km=50.0,
    )


@pytest.fixture
def manifest():
    return load_reproducibility_manifest()


# ==============================================================================
# Test 1: Reproducibility Manifest Schema and Coverage
# ==============================================================================
def test_reproducibility_manifest_schema_and_station_counts(manifest):
    """1. Manifest contains 5 stations with requested and actual grid coordinates."""
    assert manifest["manifest_metadata"]["manifest_version"] == "v2.3"
    stations = manifest["stations"]
    assert len(stations) == 5

    expected_stations = {"IND-GOA-01", "IND-BOM-01", "IND-KRW-01", "IND-MNG-01", "IND-VRL-01"}
    actual_stations = {s["station_id"] for s in stations}
    assert actual_stations == expected_stations

    for st in stations:
        assert "requested_coordinates" in st
        assert "latitude" in st["requested_coordinates"]
        assert "longitude" in st["requested_coordinates"]
        assert len(st["observations"]) >= 3

        for obs in st["observations"]:
            assert "source" in obs
            assert "variable" in obs
            assert "units" in obs
            assert "quality_flags" in obs
            assert "freshness_calculation" in obs
            assert "classification_category" in obs
            assert "operational_baseline_eligible" in obs


# ==============================================================================
# Test 2: Chlorophyll Nulls / Cloud Masking Rejected Despite HTTP 200
# ==============================================================================
def test_chlorophyll_nulls_rejected_not_inferred_from_http_200(evaluator):
    """2. Verify HTTP 200 with all nulls does NOT produce usable chlorophyll coverage."""
    # Synthetic station representing actual NOAA response (HTTP 200, 16 cells, all null)
    station_with_null_grid = {
        "station_id": "TEST-GOA-NULLS",
        "requested_coordinates": {"latitude": 15.0, "longitude": 72.0},
        "observations": [
            {
                "evidence_id": "ev-null-chla-01",
                "source": "noaa_coastwatch_erddap",
                "variable": "chlorophyll_a",
                "value": None,  # Cloud-masked raw cell null
                "unit": "mg m^-3",
                "latitude": 15.0,
                "longitude": 72.0,
                "observed_at": "2026-10-12T00:00:00Z",
                "retrieved_at": "2026-10-12T03:00:00Z",
                "status": "valid",
                "quality_flags": ["cloud_masked", "raw_cell_null"],
                "metadata": {"http_status": 200, "grid_cells_count": 16},
            }
        ],
    }

    res = evaluator.evaluate_chlorophyll_coverage([station_with_null_grid])
    assert res.status == "evaluated"
    assert res.value == 0.0  # Must be 0%, never 100%
    assert res.numerator == 0
    assert res.denominator == 1


# ==============================================================================
# Test 3: Observation Staleness Independent of Retrieval Time
# ==============================================================================
def test_observation_staleness_independent_of_retrieval(evaluator):
    """3. 10-day-old observation retrieved recently must remain stale."""
    # Satellite pass from 10 days ago (2026-10-02) retrieved today (2026-10-12)
    stale_rec = {
        "evidence_id": "ev-stale-pass-01",
        "source": "noaa_coastwatch_erddap",
        "variable": "chlorophyll_a",
        "value": 0.85,  # Valid numeric value, but old observation
        "unit": "mg m^-3",
        "latitude": 15.0,
        "longitude": 72.0,
        "observed_at": "2026-10-02T12:00:00Z",  # 240 hours ago
        "retrieved_at": "2026-10-12T03:00:00Z",  # 1 hour ago
        "status": "valid",
        "quality_flags": ["satellite_remote_sensing"],
        "metadata": {},
    }

    station = {
        "station_id": "TEST-STALE-PASS",
        "requested_coordinates": {"latitude": 15.0, "longitude": 72.0},
        "observations": [stale_rec],
    }

    res = evaluator.evaluate_chlorophyll_coverage([station])
    assert res.value == 0.0  # Excluded because observed_at > 24 hours ago


# ==============================================================================
# Test 4: Spatial Coverage Mismatch Filtering
# ==============================================================================
def test_spatial_coverage_mismatch_filtering(evaluator):
    """4. Observations diverging beyond spatial threshold are excluded from station coverage."""
    station = {
        "station_id": "TEST-GOA-MISMATCH",
        "requested_coordinates": {"latitude": 15.0, "longitude": 72.0},  # Goa
        "observations": [
            {
                "evidence_id": "ev-mismatch-chla-01",
                "source": "noaa_coastwatch_erddap",
                "variable": "chlorophyll_a",
                "value": 0.75,
                "unit": "mg m^-3",
                "latitude": 18.9,  # Mumbai coordinate (441 km away)
                "longitude": 72.8,
                "observed_at": "2026-10-12T00:00:00Z",
                "retrieved_at": "2026-10-12T03:00:00Z",
                "status": "valid",
                "quality_flags": [],
                "metadata": {},
            }
        ],
    }

    res = evaluator.evaluate_chlorophyll_coverage([station])
    assert res.value == 0.0  # Excluded due to spatial mismatch > 50 km


# ==============================================================================
# Test 5: Timestamp Preservation and Quality Flags
# ==============================================================================
def test_timestamp_preservation_and_quality_flags(manifest):
    """5. Manifest preserves both observed_at and retrieved_at and quality flags."""
    for st in manifest["stations"]:
        for obs in st["observations"]:
            if obs["observed_at"] is not None:
                assert "T" in obs["observed_at"]
                assert "Z" in obs["observed_at"] or "+00:00" in obs["observed_at"]
            if obs["retrieved_at"] is not None:
                assert "T" in obs["retrieved_at"]

            # Freshness calculation must specify policy and age
            calc = obs["freshness_calculation"]
            assert "policy" in calc
            assert "is_stale" in calc


# ==============================================================================
# Test 6: Provenance Category Partitioning
# ==============================================================================
def test_provenance_category_partitioning(manifest):
    """6. Ensure fixture and stale observations are never marked operational_baseline_eligible."""
    for st in manifest["stations"]:
        for obs in st["observations"]:
            cat = obs["classification_category"]
            assert cat in {
                "LIVE_VALIDATED",
                "CACHED_OBSERVATION",
                "STALE_OBSERVATION",
                "EMPTY_RESULT",
                "UNAVAILABLE_PROVIDER",
                "OFFLINE_FIXTURE",
            }

            # Only fresh live or fresh cached observations may be eligible
            if cat in {"STALE_OBSERVATION", "OFFLINE_FIXTURE", "UNAVAILABLE_PROVIDER"}:
                assert obs["operational_baseline_eligible"] is False


# ==============================================================================
# Test 7: Genuine Fisheries Catch Records Absence Transparency
# ==============================================================================
def test_genuine_fisheries_catch_records_absence(manifest, evaluator):
    """7. Confirm 0.0% biological telemetry coverage and unintegrated biological provider status."""
    res = evaluator.evaluate_reproducibility_manifest(manifest)
    assert res["verified_biological_coverage_pct"] == 0.0

    # Ensure all biomass entries are marked UNAVAILABLE_PROVIDER
    for st in manifest["stations"]:
        bio_obs = [o for o in st["observations"] if o["variable"] == "fish_biomass"]
        assert len(bio_obs) == 1
        assert bio_obs[0]["classification_category"] == "UNAVAILABLE_PROVIDER"
        assert bio_obs[0]["raw_value"] is None


# ==============================================================================
# Test 8: End-to-End Reproducibility Manifest Evaluation Determinism
# ==============================================================================
def test_reproducibility_manifest_evaluation_deterministic(evaluator, manifest):
    """8. Evaluate full manifest: 100% waves/SST, 0% chlorophyll, and explicit root cause."""
    res = evaluator.evaluate_reproducibility_manifest(manifest)

    assert res["total_stations"] == 5
    assert res["usable_wave_coverage_pct"] == 100.0
    assert res["usable_sst_coverage_pct"] == 100.0
    assert res["usable_chlorophyll_coverage_pct"] == 0.0
    assert res["verified_biological_coverage_pct"] == 0.0

    cats = res["category_distribution"]
    assert cats["LIVE_VALIDATED"] == 10  # 5 wave + 5 SST
    assert cats["STALE_OBSERVATION"] == 5  # 5 chlorophyll
    assert cats["UNAVAILABLE_PROVIDER"] == 5  # 5 fish biomass

    assert "cloud masking" in res["chlorophyll_root_cause"].lower()
