"""Deterministic Unit Tests for ORCA Fisheries Intelligence v2.2 Benchmark.

Verifies:
1. Benchmark dataset schema and 3-partition isolation.
2. Zero biological label transparency (withholding fictitious precision/recall/F1).
3. Empty denominator handling producing 'not_evaluable'.
4. Temporal leakage rejection (future observation timestamps beyond clock skew).
5. Spatial mismatch rejection (Great-Circle distance > 50 km).
6. Conflicting duplicate quarantine (preventing cherry-picking favorable values).
7. Stale evidence exclusion (> 24h satellite chlorophyll).
8. Fixture contamination prevention (barring fixture catalog from operational baseline).
9. Environmental species rule consistency (CMFRI/FAO thermal preferences).
10. End-to-end benchmark execution determinism.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from app.evaluation.fisheries_benchmark import (
    FisheriesBenchmarkEvaluator,
    load_benchmark_dataset,
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
def benchmark_data():
    return load_benchmark_dataset()


# ==============================================================================
# Test 1: Partition Isolation & Dataset Schema
# ==============================================================================
def test_benchmark_dataset_partition_isolation(benchmark_data):
    """1. Ensure 3 isolated partitions exist and offline fixtures cannot enter baseline."""
    assert "verified_environmental" in benchmark_data
    assert "offline_fixture_catalog" in benchmark_data
    assert "safeguard_challenge" in benchmark_data

    # Check verified environmental stations
    env_stations = benchmark_data["verified_environmental"]
    assert len(env_stations) >= 5
    for st in env_stations:
        # Ground-truth biological labels must be explicitly None in operational data
        assert st["biological_presence_label"] is None

    # Check offline fixtures are explicitly tagged
    fixtures = benchmark_data["offline_fixture_catalog"]
    assert len(fixtures) >= 2
    for fix in fixtures:
        assert fix["is_offline_fixture"] is True
        assert fix["operational_baseline_eligible"] is False
        assert "offline_fixture" in fix["quality_flags"]


# ==============================================================================
# Test 2: Honest Biological Presence Reporting & Withheld F1
# ==============================================================================
def test_zero_biological_telemetry_honest_coverage(evaluator, benchmark_data):
    """2. Confirm 0.0% biological telemetry coverage and not_evaluable classification metrics."""
    env_stations = benchmark_data["verified_environmental"]

    bio_res = evaluator.evaluate_biological_presence_coverage(env_stations)
    assert bio_res.status == "evaluated"
    assert bio_res.value == 0.0
    assert bio_res.numerator == 0
    assert bio_res.denominator == len(env_stations)

    # Classification accuracy (Precision/Recall/F1) must be NOT EVALUABLE, never fabricated
    acc_res = evaluator.evaluate_classification_accuracy(env_stations)
    assert acc_res.status == "not_evaluable"
    assert acc_res.value is None
    assert acc_res.denominator == 0
    assert "NOT EVALUABLE" in acc_res.interpretation


# ==============================================================================
# Test 3: Empty Denominator Produces 'not_evaluable'
# ==============================================================================
def test_empty_denominator_handling_explicit_not_evaluable(evaluator):
    """3. Verify that empty station/record lists return not_evaluable rather than 0% or 100%."""
    res_wave_sst = evaluator.evaluate_wave_sst_coverage([])
    assert res_wave_sst.status == "not_evaluable"
    assert res_wave_sst.value is None
    assert res_wave_sst.denominator == 0

    res_chla = evaluator.evaluate_chlorophyll_coverage([])
    assert res_chla.status == "not_evaluable"
    assert res_chla.value is None
    assert res_chla.denominator == 0

    res_bio = evaluator.evaluate_biological_presence_coverage([])
    assert res_bio.status == "not_evaluable"
    assert res_bio.value is None
    assert res_bio.denominator == 0

    res_rule = evaluator.evaluate_environmental_rule_consistency([])
    assert res_rule.status == "not_evaluable"
    assert res_rule.value is None
    assert res_rule.denominator == 0


# ==============================================================================
# Test 4: Temporal Leakage Rejection Safeguard
# ==============================================================================
def test_temporal_leakage_safeguard_rejection(evaluator, benchmark_data):
    """4. Ensure future-dated observations beyond clock skew are 100% rejected."""
    challenges = benchmark_data["safeguard_challenge"]
    res = evaluator.evaluate_temporal_leakage_safeguard(challenges)

    assert res.status == "evaluated"
    assert res.value == 1.0  # 100% rejection rate
    assert res.numerator == 2
    assert res.denominator == 2


# ==============================================================================
# Test 5: Spatial Mismatch Rejection Safeguard
# ==============================================================================
def test_spatial_mismatch_safeguard_quarantine(evaluator, benchmark_data):
    """5. Ensure observations diverging > 50 km Great-Circle distance are quarantined."""
    challenges = benchmark_data["safeguard_challenge"]
    res = evaluator.evaluate_spatial_mismatch_safeguard(challenges)

    assert res.status == "evaluated"
    assert res.value == 1.0  # 100% rejection rate
    assert res.numerator == 1
    assert res.denominator == 1


# ==============================================================================
# Test 6: Stale Satellite Observation Exclusion
# ==============================================================================
def test_stale_satellite_observation_exclusion(evaluator, benchmark_data):
    """6. Ensure satellite chlorophyll observations older than 24h are excluded from baseline."""
    challenges = benchmark_data["safeguard_challenge"]
    res = evaluator.evaluate_stale_evidence_exclusion(challenges)

    assert res.status == "evaluated"
    assert res.value == 1.0
    assert res.numerator == 1
    assert res.denominator == 1


# ==============================================================================
# Test 7: Conflicting Duplicate Quarantine (No Cherry-Picking)
# ==============================================================================
def test_conflicting_duplicate_handling_no_cherry_picking(evaluator, benchmark_data):
    """7. Ensure conflicting duplicate values are quarantined rather than cherry-picking favorable ones."""
    challenges = benchmark_data["safeguard_challenge"]
    res = evaluator.evaluate_duplicate_conflict_handling(challenges)

    assert res.status == "evaluated"
    assert res.value == 1.0
    assert res.numerator == 1
    assert res.denominator == 1
    # Check details guarantee no cherry picking
    case_detail = res.details["cases"][0]
    assert case_detail["action"] == "FLAGGED_CONFLICT_QUARANTINED"
    assert case_detail["cherry_picked"] is False


# ==============================================================================
# Test 8: Fixture Contamination Prevention
# ==============================================================================
def test_fixture_contamination_prevention(evaluator, benchmark_data):
    """8. Ensure offline fixture catalog items cannot enter operational baseline."""
    fixtures = benchmark_data["offline_fixture_catalog"]
    challenges = benchmark_data["safeguard_challenge"]
    res = evaluator.evaluate_fixture_contamination_prevention(fixtures, challenges)

    assert res.status == "evaluated"
    assert res.value == 1.0
    assert res.numerator == len(fixtures) + 1  # 2 fixtures + 1 probe
    assert res.denominator == len(fixtures) + 1


# ==============================================================================
# Test 9: Species Environmental Rule Consistency
# ==============================================================================
def test_species_environmental_rule_consistency(evaluator, benchmark_data):
    """9. Verify 100% consistency against documented CMFRI/FAO thermal limits."""
    env_stations = benchmark_data["verified_environmental"]
    res = evaluator.evaluate_environmental_rule_consistency(env_stations)

    assert res.status == "evaluated"
    assert res.value == 1.0
    assert res.numerator == len(env_stations)
    assert res.denominator == len(env_stations)


# ==============================================================================
# Test 10: Master Benchmark Execution Determinism
# ==============================================================================
def test_full_benchmark_run_deterministic_execution(evaluator, benchmark_data):
    """10. Verify end-to-end benchmark execution yields structured report with all safeguards passed."""
    report = evaluator.run_benchmark(benchmark_data)

    assert report["all_safeguards_passed"] is True
    assert report["metrics_evaluated_count"] == 9
    assert report["metrics_not_evaluable_count"] == 1
    assert len(report["metrics"]) == 10

    # Ensure accuracy metric is specifically not_evaluable
    acc_metric = next(m for m in report["metrics"] if m["metric_id"] == "acc_biological_classification")
    assert acc_metric["status"] == "not_evaluable"
    assert acc_metric["value"] is None

    # Check limitations documented
    assert any("biological" in lim.lower() for lim in report["limitations_and_caveats"])
