"""Targeted Unit Tests for ORCA Fisheries Intelligence v2.8 Hardening.

Verifies:
1. Unauthorized / invalid records are never committed to the adapter operational store or returned by fetch.
2. UTF-8 BOM headers (\ufeff) in CSV exports are cleaned and resolved seamlessly.
3. Negative spatial uncertainty, negative catch weight, and non-positive effort hours are rejected with explicit reason codes.
4. Benchmark classification accuracy with ground-truth labels but missing predictions returns strictly NOT_EVALUABLE.
5. Benchmark classification accuracy with valid predictions computes true Precision, Recall, F1, and Accuracy.
"""

from datetime import datetime, timezone
import pytest

from app.data_sources.biological_adapter import (
    AuthorizedFisheriesAdapter,
    BiologicalObservationMethod,
    RawBiologicalFisheriesRecord,
)
from app.data_sources.ground_truth_import import (
    GroundTruthCsvImporter,
    _resolve_header_mapping,
)
from app.evaluation.fisheries_benchmark import FisheriesBenchmarkEvaluator

FIXED_NOW = datetime(2026, 10, 13, 0, 0, 0, tzinfo=timezone.utc)


def test_unauthorized_record_never_committed_to_store():
    """1. Ensure unauthorized record (is_authorized_official_feed=False) is never added to store."""
    adapter = AuthorizedFisheriesAdapter()
    assert len(adapter._normalized_records) == 0

    unauth_rec = RawBiologicalFisheriesRecord(
        source_agency="UNAUTHORIZED-FEED",
        dataset_identifier="scraping-test",
        record_identifier="unauth-001",
        observation_method=BiologicalObservationMethod.COMMERCIAL_LANDING_STATISTIC,
        species_raw_name="Indian Mackerel",
        latitude=15.0,
        longitude=72.0,
        spatial_uncertainty_km=10.0,
        observed_at=FIXED_NOW,
        catch_weight_kg=100.0,
        effort_hours=4.0,
        is_authorized_official_feed=False,
    )

    ev, issues = adapter.normalize_record(unauth_rec, now=FIXED_NOW, commit=True)
    assert issues == []
    assert ev is not None
    assert ev.status == "invalid"
    # Operational store MUST remain strictly empty
    assert len(adapter._normalized_records) == 0


def test_utf8_bom_header_handling():
    """2. Verify UTF-8 BOM prefix (\\ufeff) in headers is stripped and mapped to canonical fields."""
    headers_with_bom = [
        "\ufeffrecord_identifier",
        "source_agency",
        "dataset_identifier",
        "observation_method",
        "species_name",
        "latitude",
        "longitude",
        "observed_at",
        "catch_weight",
        "catch_unit",
        "effort_value",
        "effort_unit",
        "is_authorized",
    ]
    mapping, missing = _resolve_header_mapping(headers_with_bom)
    assert missing == []
    assert "record_identifier" in mapping
    assert mapping["record_identifier"] == "\ufeffrecord_identifier"


def test_negative_numerical_bounds_rejected():
    """3. Verify negative spatial uncertainty, catch weight, and effort hours are rejected."""
    importer = GroundTruthCsvImporter()
    csv_content = (
        "record_identifier,source_agency,dataset_identifier,observation_method,species_name,"
        "latitude,longitude,spatial_uncertainty_km,observed_at,catch_weight,catch_unit,effort_value,effort_unit,is_authorized\n"
        "r1,ICAR-CMFRI,d1,COMMERCIAL_LANDING_STATISTIC,Indian Mackerel,15.0,72.0,-5.0,2026-10-12T00:00:00Z,100,kg,5,hours,true\n"
        "r2,ICAR-CMFRI,d1,COMMERCIAL_LANDING_STATISTIC,Indian Mackerel,15.0,72.0,5.0,2026-10-12T00:00:00Z,-10,kg,5,hours,true\n"
        "r3,ICAR-CMFRI,d1,COMMERCIAL_LANDING_STATISTIC,Indian Mackerel,15.0,72.0,5.0,2026-10-12T00:00:00Z,100,kg,-2,hours,true\n"
    )
    summary = importer.import_csv(csv_content, is_dry_run=True, now=FIXED_NOW)
    assert summary.total_rows == 3
    assert summary.accepted_rows == 0
    assert summary.rejected_rows == 3

    assert "negative_spatial_uncertainty" in summary.summary_reasons
    assert "negative_catch_weight" in summary.summary_reasons
    assert "non_positive_effort_hours" in summary.summary_reasons


def test_benchmark_accuracy_with_labels_but_missing_predictions():
    """4. If ground-truth labels exist but predictions are missing, classification accuracy remains NOT_EVALUABLE."""
    evaluator = FisheriesBenchmarkEvaluator(reference_time=FIXED_NOW)
    stations_with_labels_only = [
        {"station_id": "ST1", "biological_presence_label": "PRESENT"},
        {"station_id": "ST2", "biological_presence_label": "ABSENT"},
    ]
    res = evaluator.evaluate_classification_accuracy(stations_with_labels_only)
    assert res.status == "not_evaluable"
    assert res.value is None
    assert "model predictions absent" in res.interpretation


def test_benchmark_accuracy_computes_true_metrics():
    """5. When both ground-truth labels and model predictions are supplied, computes true confusion matrix."""
    evaluator = FisheriesBenchmarkEvaluator(reference_time=FIXED_NOW)
    stations = [
        {"station_id": "ST1", "biological_presence_label": "PRESENT", "predicted_presence_label": "PRESENT"},  # TP
        {"station_id": "ST2", "biological_presence_label": "ABSENT", "predicted_presence_label": "ABSENT"},    # TN
        {"station_id": "ST3", "biological_presence_label": "PRESENT", "predicted_presence_label": "ABSENT"},  # FN
        {"station_id": "ST4", "biological_presence_label": "ABSENT", "predicted_presence_label": "PRESENT"},   # FP
    ]
    res = evaluator.evaluate_classification_accuracy(stations)
    assert res.status == "evaluated"
    assert res.value == 0.5  # (1 TP + 1 TN) / 4 = 0.5
    assert res.details["tp"] == 1
    assert res.details["tn"] == 1
    assert res.details["fp"] == 1
    assert res.details["fn"] == 1
    assert res.details["precision"] == 0.5
    assert res.details["recall"] == 0.5
    assert res.details["f1"] == 0.5


def test_fao_species_codes_resolution():
    """6. FAO 3-alpha codes (RAK, IOS, POA, YFT, SKJ, DUC) resolve cleanly via registry and CSV importer."""
    from app.agents.species_rules import lookup_species

    # Direct FAO code resolution
    assert lookup_species("RAK")["status"] == "SUPPORTED"
    assert lookup_species("RAK")["resolved_name"] == "Indian Mackerel"

    assert lookup_species("IOS")["status"] == "SUPPORTED"
    assert lookup_species("IOS")["resolved_name"] == "Indian Oil Sardine"

    assert lookup_species("POA")["status"] == "SUPPORTED"
    assert lookup_species("POA")["resolved_name"] == "Silver Pomfret"

    assert lookup_species("YFT")["status"] == "SUPPORTED"
    assert "Tuna" in lookup_species("YFT")["resolved_name"]

    assert lookup_species("SKJ")["status"] == "SUPPORTED"
    assert "Tuna" in lookup_species("SKJ")["resolved_name"]

    assert lookup_species("DUC")["status"] == "SUPPORTED"
    assert lookup_species("DUC")["resolved_name"] == "Bombay Duck"

    # CSV import with FAO column
    importer = GroundTruthCsvImporter()
    csv_content = (
        "record_identifier,source_agency,dataset_identifier,observation_method,species_name,fao_alpha3_code,"
        "latitude,longitude,spatial_uncertainty_km,observed_at,catch_weight,catch_unit,effort_value,effort_unit,is_authorized\n"
        "r-rak,ICAR-CMFRI,d1,COMMERCIAL_LANDING_STATISTIC,Mackerel,RAK,15.5,73.8,10.0,2026-10-12T00:00:00Z,200,kg,4,hours,true\n"
        "r-poa,ICAR-CMFRI,d1,COMMERCIAL_LANDING_STATISTIC,Pomfret,POA,15.5,73.8,10.0,2026-10-12T00:00:00Z,150,kg,4,hours,true\n"
    )
    summary = importer.import_csv(csv_content, is_dry_run=True, now=FIXED_NOW)
    assert summary.total_rows == 2
    assert summary.accepted_rows == 2
    assert summary.rejected_rows == 0
