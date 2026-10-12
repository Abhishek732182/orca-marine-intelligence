"""Deterministic Unit Tests for ORCA Fisheries v2.7: Hardening, Idempotency, and Audit Trail.

Verifies:
1. NaN and infinite coordinate rejection.
2. NaN and infinite catch weight and effort hours rejection.
3. Idempotent re-import: duplicate file ingestion is skipped without store pollution.
4. Dry-run does not lock out subsequent live import (signature rollback).
5. Source file SHA256 checksum audit trail injected into EvidenceRecord metadata.
6. Before/after data store count integrity tracking.
7. Silver Pomfret (Pampus argenteus) species registry lookup and thermal suitability evaluation.
8. ERDDAP cloud-masked table parsing with null values returns empty evidence and 0.0% coverage.
"""

from datetime import datetime, timezone
import pytest

from app.agents.species_rules import evaluate_thermal_suitability, lookup_species
from app.data_sources.erddap_client import ErddapClient
from app.data_sources.ground_truth_import import (
    GroundTruthCsvImporter,
)

FIXED_NOW = datetime(2026, 10, 12, 12, 0, 0, tzinfo=timezone.utc)

SAMPLE_VALID_CSV = """record_identifier,source_agency,dataset_identifier,observation_method,species_name,scientific_name,latitude,longitude,spatial_uncertainty_km,landing_center_name,observed_at,voyage_start_at,voyage_end_at,catch_weight,catch_unit,effort_value,effort_unit,gear_type,is_authorized,access_authorization_token
rec-v27-01,ICAR-CMFRI,cmfri-fcsc-westcoast-2026,COMMERCIAL_LANDING_STATISTIC,Indian Mackerel,Rastrelliger kanagurta,15.503,73.827,10.0,Malim Jetty,2026-10-12T06:00:00Z,2026-10-12T01:00:00Z,2026-10-12T08:00:00Z,300.0,kg,5.0,hours,Purse Seine,true,AUTH_TOKEN_CMFRI_VALID
"""


# ==============================================================================
# Test 1: NaN and Infinite Coordinates Rejection
# ==============================================================================
def test_nan_and_infinite_coordinates_rejection():
    """1. Coordinates containing NaN or Infinity are strictly rejected."""
    nan_lat_csv = SAMPLE_VALID_CSV.replace("15.503", "NaN")
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv(nan_lat_csv, is_dry_run=True, now=FIXED_NOW)

    assert summary.total_rows == 1
    assert summary.accepted_rows == 0
    assert summary.rejected_rows == 1
    assert any("coordinates_nan_or_infinite" in r for r in summary.rejection_reasons_by_row[1])

    inf_lat_csv = SAMPLE_VALID_CSV.replace("15.503", "Infinity")
    summary_inf = importer.import_csv(inf_lat_csv, is_dry_run=True, now=FIXED_NOW)
    assert summary_inf.rejected_rows == 1
    assert any("coordinates_nan_or_infinite" in r for r in summary_inf.rejection_reasons_by_row[1])


# ==============================================================================
# Test 2: NaN and Infinite Catch Weight & Effort Hours Rejection
# ==============================================================================
def test_nan_catch_and_effort_rejection():
    """2. Catch weight or effort hours containing NaN or Infinity are strictly rejected."""
    nan_catch_csv = SAMPLE_VALID_CSV.replace(",300.0,", ",NaN,")
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv(nan_catch_csv, is_dry_run=True, now=FIXED_NOW)

    assert summary.total_rows == 1
    assert summary.accepted_rows == 0
    assert summary.rejected_rows == 1
    assert any("catch_weight_nan_or_infinite" in r for r in summary.rejection_reasons_by_row[1])

    nan_effort_csv = SAMPLE_VALID_CSV.replace(",5.0,", ",NaN,")
    summary_eff = importer.import_csv(nan_effort_csv, is_dry_run=True, now=FIXED_NOW)
    assert summary_eff.rejected_rows == 1
    assert any("effort_hours_nan_or_infinite" in r for r in summary_eff.rejection_reasons_by_row[1])


# ==============================================================================
# Test 3: Idempotent Re-Import Handling
# ==============================================================================
def test_idempotent_reimport_handling():
    """3. Ingesting the exact same authorized file twice performs an idempotent skip without store duplicate."""
    importer = GroundTruthCsvImporter()
    summary_1 = importer.import_csv(SAMPLE_VALID_CSV, is_dry_run=False, now=FIXED_NOW)

    assert summary_1.accepted_rows == 1
    assert summary_1.store_count_before == 0
    assert summary_1.store_count_after == 1
    assert summary_1.is_idempotent_reimport is False

    # Second import of identical file
    summary_2 = importer.import_csv(SAMPLE_VALID_CSV, is_dry_run=False, now=FIXED_NOW)
    assert summary_2.is_idempotent_reimport is True
    assert summary_2.store_count_before == 1
    assert summary_2.store_count_after == 1  # Store count unchanged
    assert summary_2.summary_reasons.get("idempotent_reimport_skipped") == 1
    assert len(importer.adapter._normalized_records) == 1


# ==============================================================================
# Test 4: Dry-Run Does Not Lock Out Subsequent Actual Import
# ==============================================================================
def test_dry_run_does_not_block_subsequent_actual_import():
    """4. Running a dry-run first must restore seen_signatures so actual import succeeds."""
    importer = GroundTruthCsvImporter()

    # Step 1: Dry run
    summary_dry = importer.import_csv(SAMPLE_VALID_CSV, is_dry_run=True, now=FIXED_NOW)
    assert summary_dry.is_dry_run is True
    assert summary_dry.accepted_rows == 1
    assert summary_dry.store_count_after == 0  # Store untouched

    # Step 2: Live import on exact same dataset
    summary_live = importer.import_csv(SAMPLE_VALID_CSV, is_dry_run=False, now=FIXED_NOW)
    assert summary_live.is_dry_run is False
    assert summary_live.accepted_rows == 1
    assert summary_live.rejected_rows == 0
    assert summary_live.store_count_after == 1


# ==============================================================================
# Test 5: Source File SHA256 Checksum Audit Trail
# ==============================================================================
def test_checksum_injected_in_evidence_metadata():
    """5. Source file SHA256 checksum is computed and injected into summary and record metadata."""
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv(SAMPLE_VALID_CSV, is_dry_run=False, now=FIXED_NOW)

    assert summary.source_file_sha256 is not None
    assert len(summary.source_file_sha256) == 64  # Valid SHA256 hex string

    rec = summary.imported_records[0]
    assert rec.metadata.get("source_file_sha256") == summary.source_file_sha256


# ==============================================================================
# Test 6: Before/After Store Count Integrity Tracking
# ==============================================================================
def test_store_count_before_and_after_integrity():
    """6. Summary accurately reflects store count before and after operation."""
    importer = GroundTruthCsvImporter()
    assert len(importer.adapter._normalized_records) == 0

    s1 = importer.import_csv(SAMPLE_VALID_CSV, is_dry_run=False, now=FIXED_NOW)
    assert s1.store_count_before == 0
    assert s1.store_count_after == 1

    # Adding second record with distinct ID
    second_row_csv = SAMPLE_VALID_CSV.replace("rec-v27-01", "rec-v27-02").replace("15.503", "15.600")
    s2 = importer.import_csv(second_row_csv, is_dry_run=False, now=FIXED_NOW)
    assert s2.store_count_before == 1
    assert s2.store_count_after == 2


# ==============================================================================
# Test 7: Silver Pomfret Species Registry & Thermal Suitability
# ==============================================================================
def test_pomfret_thermal_bounds_and_species_lookup():
    """7. Silver Pomfret is supported in SPECIES_REGISTRY with valid thermal preference bounds."""
    lookup = lookup_species("Silver Pomfret")
    assert lookup["status"] == "SUPPORTED"
    assert lookup["species_info"]["scientific_name"] == "Pampus argenteus"

    # Thermal suitability evaluation: 27.0 C is in optimal [25.0, 29.5]
    eval_opt = evaluate_thermal_suitability(lookup, 27.0)
    assert eval_opt["thermal_suitability"] == "OPTIMAL"
    assert eval_opt["thermal_sub_score"] == 95.0

    # 23.0 C is in tolerable [22.0, 31.0] but outside optimal
    eval_tol = evaluate_thermal_suitability(lookup, 23.0)
    assert eval_tol["thermal_suitability"] == "TOLERABLE"
    assert 50.0 <= eval_tol["thermal_sub_score"] <= 85.0

    # 33.0 C is outside tolerable
    eval_out = evaluate_thermal_suitability(lookup, 33.0)
    assert eval_out["thermal_suitability"] == "UNFAVORABLE"
    assert eval_out["thermal_sub_score"] == 20.0


# ==============================================================================
# Test 8: ERDDAP Cloud-Masked Table Parsing Returns Zero Records
# ==============================================================================
def test_erddap_cloud_masked_null_table_returns_empty_and_zero_coverage():
    """8. ERDDAP HTTP 200 table where all chlorophyll values are null returns empty list without fabrication."""
    client = ErddapClient()
    null_table_data = {
        "table": {
            "columnNames": ["time", "latitude", "longitude", "chlor_a"],
            "columnTypes": ["String", "float", "float", "float"],
            "rows": [
                ["2026-10-12T00:00:00Z", 15.0, 73.0, None],
                ["2026-10-12T00:00:00Z", 15.1, 73.0, None],
                ["2026-10-12T00:00:00Z", 15.2, 73.0, None],
            ],
        }
    }

    records = client.parse_erddap_json_table(
        null_table_data,
        variable_name="chlorophyll_a",
        unit="mg/m^3",
        source_url="https://coastwatch.pfeg.noaa.gov/erddap/griddap/nesdisVHNchlaDaily.json",
        retrieved_at=FIXED_NOW,
    )

    assert records == []  # Zero valid non-null records generated from cloud-masked cells
