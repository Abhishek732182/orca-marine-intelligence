"""Deterministic Unit Tests for ORCA Fisheries v2.5: Ground-Truth Import & Benchmark Readiness.

Verifies:
1. Empty files rejection.
2. Malformed schemas & missing required headers.
3. Unsupported / unverified species identification rejection.
4. Duplicate rows rejection within CSV batch.
5. Invalid coordinates (out-of-bounds & unparseable) rejection.
6. Future timestamp integrity rejection.
7. Incompatible effort units (e.g., 'days' instead of 'hours') rejection.
8. Incompatible catch units rejection.
9. Missing catch data rejection.
10. Unauthorized provenance quarantine (status invalid, unverified feed).
11. Valid authorized records normalization & exact CPUE derivation (kg/hour).
12. Dry-run validation mode reporting without committing operational storage.
13. Benchmark split leakage validator: catches duplicate leakage and temporal leakage.
14. Environmental chlorophyll linkage preserves strict 24-hour freshness rule.
"""

from datetime import datetime, timedelta, timezone
import pytest

from app.data_sources.ground_truth_import import (
    BenchmarkPartitionValidator,
    GroundTruthCsvImporter,
    verify_environmental_linkage_freshness,
)
from app.schemas.evidence import EvidenceRecord

FIXED_NOW = datetime(2026, 10, 12, 12, 0, 0, tzinfo=timezone.utc)


SAMPLE_VALID_CSV = """record_identifier,source_agency,dataset_identifier,observation_method,species_name,scientific_name,latitude,longitude,spatial_uncertainty_km,landing_center_name,observed_at,voyage_start_at,voyage_end_at,catch_weight,catch_unit,effort_value,effort_unit,gear_type,is_authorized,access_authorization_token
rec-cmfri-001,ICAR-CMFRI,cmfri-fcsc-westcoast-2026,COMMERCIAL_LANDING_STATISTIC,Indian Mackerel,Rastrelliger kanagurta,15.503,73.827,10.0,Malim Jetty,2026-10-12T06:00:00Z,2026-10-12T01:00:00Z,2026-10-12T08:00:00Z,300.0,kg,5.0,hours,Purse Seine,true,AUTH_TOKEN_CMFRI_VALID
"""


# ==============================================================================
# Test 1: Empty File Handling
# ==============================================================================
def test_import_empty_file():
    """1. Empty CSV input returns zero rows and an explicit 'empty_file' summary reason."""
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv("", is_dry_run=True, now=FIXED_NOW)

    assert summary.total_rows == 0
    assert summary.accepted_rows == 0
    assert summary.summary_reasons.get("empty_file") == 1
    assert summary.missing_required_headers == []


# ==============================================================================
# Test 2: Missing Required Header Columns
# ==============================================================================
def test_import_missing_required_headers():
    """2. CSV with missing required columns is rejected with explicit header list."""
    incomplete_csv = """species_name,latitude,longitude,catch_weight
Indian Mackerel,15.5,73.8,100.0
"""
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv(incomplete_csv, is_dry_run=True, now=FIXED_NOW)

    assert summary.total_rows == 0
    assert "record_identifier" in summary.missing_required_headers
    assert "source_agency" in summary.missing_required_headers
    assert "observation_method" in summary.missing_required_headers
    assert "effort_value" in summary.missing_required_headers


# ==============================================================================
# Test 3: Unsupported Species Identification
# ==============================================================================
def test_import_unsupported_species_rejection():
    """3. Records with unrecognized species names are rejected by taxonomic quality gate."""
    csv_content = SAMPLE_VALID_CSV.replace(
        "Indian Mackerel,Rastrelliger kanagurta",
        "Cryptic Mythological Fish,Crypticus mythologicus",
    )
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv(csv_content, is_dry_run=True, now=FIXED_NOW)

    assert summary.total_rows == 1
    assert summary.accepted_rows == 0
    assert summary.rejected_rows == 1
    assert any("unsupported_or_unverified_species" in r for r in summary.rejection_reasons_by_row[1])


# ==============================================================================
# Test 4: Duplicate Rows Within Batch
# ==============================================================================
def test_import_duplicate_rows_rejection():
    """4. Repeated spatio-temporal-species observation is rejected as duplicate."""
    two_identical_rows_csv = SAMPLE_VALID_CSV + """rec-cmfri-002,ICAR-CMFRI,cmfri-fcsc-westcoast-2026,COMMERCIAL_LANDING_STATISTIC,Indian Mackerel,Rastrelliger kanagurta,15.503,73.827,10.0,Malim Jetty,2026-10-12T06:00:00Z,2026-10-12T01:00:00Z,2026-10-12T08:00:00Z,300.0,kg,5.0,hours,Purse Seine,true,AUTH_TOKEN_CMFRI_VALID
"""
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv(two_identical_rows_csv, is_dry_run=True, now=FIXED_NOW)

    assert summary.total_rows == 2
    assert summary.accepted_rows == 1
    assert summary.rejected_rows == 1
    assert "duplicate_record_detected" in summary.rejection_reasons_by_row[2]


# ==============================================================================
# Test 5: Invalid Coordinates (Out-of-Bounds & Unparseable)
# ==============================================================================
def test_import_invalid_coordinates():
    """5. Out-of-bounds coordinates (lat 95.0) are rejected."""
    csv_content = SAMPLE_VALID_CSV.replace("15.503", "95.503")
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv(csv_content, is_dry_run=True, now=FIXED_NOW)

    assert summary.total_rows == 1
    assert summary.accepted_rows == 0
    assert summary.rejected_rows == 1
    assert any("coordinates_out_of_bounds" in r for r in summary.rejection_reasons_by_row[1])


# ==============================================================================
# Test 6: Future Timestamp Rejection
# ==============================================================================
def test_import_future_timestamp_rejection():
    """6. Observations with timestamps occurring in the future relative to ref_time are rejected."""
    future_time_str = (FIXED_NOW + timedelta(days=2)).isoformat()
    csv_content = SAMPLE_VALID_CSV.replace("2026-10-12T06:00:00Z", future_time_str)
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv(csv_content, is_dry_run=True, now=FIXED_NOW)

    assert summary.total_rows == 1
    assert summary.accepted_rows == 0
    assert summary.rejected_rows == 1
    assert any("observation_timestamp_in_future" in r for r in summary.rejection_reasons_by_row[1])


# ==============================================================================
# Test 7: Incompatible Effort Units (e.g. 'days' or 'nets')
# ==============================================================================
def test_import_incompatible_effort_units():
    """7. Effort provided in non-hourly units ('days') is rejected without conversion assumptions."""
    csv_content = SAMPLE_VALID_CSV.replace(",hours,", ",days,")
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv(csv_content, is_dry_run=True, now=FIXED_NOW)

    assert summary.total_rows == 1
    assert summary.accepted_rows == 0
    assert summary.rejected_rows == 1
    assert any("incompatible_effort_units" in r for r in summary.rejection_reasons_by_row[1])


# ==============================================================================
# Test 8: Incompatible Catch Units (e.g. 'baskets')
# ==============================================================================
def test_import_incompatible_catch_units():
    """8. Catch provided in non-standard units ('baskets') is rejected."""
    csv_content = SAMPLE_VALID_CSV.replace(",kg,", ",baskets,")
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv(csv_content, is_dry_run=True, now=FIXED_NOW)

    assert summary.total_rows == 1
    assert summary.accepted_rows == 0
    assert summary.rejected_rows == 1
    assert any("incompatible_catch_units" in r for r in summary.rejection_reasons_by_row[1])


# ==============================================================================
# Test 9: Missing Catch Metric
# ==============================================================================
def test_import_missing_catch_metrics():
    """9. Record with empty catch weight is rejected by the missing value gate."""
    # Replace catch weight '300.0' with empty string ''
    csv_content = SAMPLE_VALID_CSV.replace(",300.0,", ",,")
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv(csv_content, is_dry_run=True, now=FIXED_NOW)

    assert summary.total_rows == 1
    assert summary.accepted_rows == 0
    assert summary.rejected_rows == 1
    assert any("missing_catch_and_biomass_metrics" in r for r in summary.rejection_reasons_by_row[1])


# ==============================================================================
# Test 10: Unauthorized Provenance Quarantine
# ==============================================================================
def test_import_unauthorized_provenance_quarantine():
    """10. Unverified or unauthorized feeds are quarantined as invalid, not accepted."""
    csv_content = SAMPLE_VALID_CSV.replace(",true,", ",false,")
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv(csv_content, is_dry_run=True, now=FIXED_NOW)

    assert summary.total_rows == 1
    assert summary.accepted_rows == 0
    assert summary.quarantined_rows == 1
    assert summary.rejected_rows == 0
    assert any("unauthorized_or_unverified_feed" in r for r in summary.rejection_reasons_by_row[1])


# ==============================================================================
# Test 11: Valid Authorized Record Normalization & CPUE Derivation
# ==============================================================================
def test_import_valid_authorized_record():
    """11. Valid authorized record is accepted, and CPUE is derived exactly as catch_kg / effort_hours."""
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv(SAMPLE_VALID_CSV, is_dry_run=False, now=FIXED_NOW)

    assert summary.total_rows == 1
    assert summary.accepted_rows == 1
    assert summary.rejected_rows == 0
    assert summary.quarantined_rows == 0
    assert summary.is_authorized_dataset is True
    assert len(summary.imported_records) == 1

    rec = summary.imported_records[0]
    assert rec.status == "valid"
    assert rec.variable == "fish_catch_weight"
    assert rec.value == 300.0
    assert rec.unit == "kg"
    assert rec.metadata["canonical_species"] == "Indian Mackerel"
    assert rec.metadata["cpue_kg_per_hour"] == 60.0  # 300.0 / 5.0
    assert "official_authorized_telemetry" in rec.quality_flags


# ==============================================================================
# Test 12: Dry-Run Mode Reporting
# ==============================================================================
def test_import_dry_run_mode_does_not_commit():
    """12. Dry-run mode validates rows fully but leaves imported_records uncommitted."""
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv(SAMPLE_VALID_CSV, is_dry_run=True, now=FIXED_NOW)

    assert summary.is_dry_run is True
    assert summary.accepted_rows == 1
    assert len(summary.imported_records) == 0  # Not stored in dry-run mode


# ==============================================================================
# Test 13: Benchmark Partition Validator (Leakage Prevention)
# ==============================================================================
def test_benchmark_partition_validator_leakage_detection():
    """13. Benchmark partition validator detects duplicate and temporal leakage."""
    r1 = EvidenceRecord(
        evidence_id="e1",
        source="fisheries-cmfri",
        source_record_id="rec-001",
        variable="fish_catch_weight",
        value=100.0,
        unit="kg",
        latitude=15.0,
        longitude=73.0,
        observed_at=datetime(2026, 10, 10, 10, 0, 0, tzinfo=timezone.utc),
        retrieved_at=FIXED_NOW,
        status="valid",
    )
    r2_duplicate = EvidenceRecord(
        evidence_id="e2",
        source="fisheries-cmfri",
        source_record_id="rec-001",
        variable="fish_catch_weight",
        value=100.0,
        unit="kg",
        latitude=15.0,
        longitude=73.0,
        observed_at=datetime(2026, 10, 10, 10, 0, 0, tzinfo=timezone.utc),
        retrieved_at=FIXED_NOW,
        status="valid",
    )
    r3_temporal_leak = EvidenceRecord(
        evidence_id="e3",
        source="fisheries-cmfri",
        source_record_id="rec-003",
        variable="fish_catch_weight",
        value=150.0,
        unit="kg",
        latitude=15.5,
        longitude=73.5,
        observed_at=datetime(2026, 10, 9, 10, 0, 0, tzinfo=timezone.utc),  # Earlier than train max (Oct 10)
        retrieved_at=FIXED_NOW,
        status="valid",
    )
    r4_valid_eval = EvidenceRecord(
        evidence_id="e4",
        source="fisheries-cmfri",
        source_record_id="rec-004",
        variable="fish_catch_weight",
        value=180.0,
        unit="kg",
        latitude=16.0,
        longitude=73.2,
        observed_at=datetime(2026, 10, 12, 10, 0, 0, tzinfo=timezone.utc),  # After train max (Oct 10)
        retrieved_at=FIXED_NOW,
        status="valid",
    )

    # A. Duplicate leakage
    report_dup = BenchmarkPartitionValidator.validate_partition_split(
        train_records=[r1],
        eval_records=[r2_duplicate],
        split_method="temporal_cutoff",
    )
    assert report_dup.is_valid_split is False
    assert any("duplicate_leakage_detected" in w for w in report_dup.leakage_warnings)

    # B. Temporal leakage
    report_temp = BenchmarkPartitionValidator.validate_partition_split(
        train_records=[r1],
        eval_records=[r3_temporal_leak],
        split_method="temporal_cutoff",
    )
    assert report_temp.is_valid_split is False
    assert any("temporal_leakage_detected" in w for w in report_temp.leakage_warnings)

    # C. Clean valid split
    report_clean = BenchmarkPartitionValidator.validate_partition_split(
        train_records=[r1],
        eval_records=[r4_valid_eval],
        split_method="temporal_cutoff",
    )
    assert report_clean.is_valid_split is True
    assert report_clean.leakage_warnings == []


# ==============================================================================
# Test 14: Environmental Chlorophyll Freshness Window Preservation
# ==============================================================================
def test_chlorophyll_linkage_freshness_preservation():
    """14. Satellite chlorophyll paired records older than 24 hours are verified stale."""
    fresh_chla = EvidenceRecord(
        evidence_id="chla-fresh",
        source="erddap-satellite",
        variable="chlorophyll_a",
        value=0.45,
        unit="mg/m^3",
        latitude=15.0,
        longitude=73.0,
        observed_at=FIXED_NOW - timedelta(hours=12),  # 12h old (<24h)
        retrieved_at=FIXED_NOW,
        status="valid",
    )
    stale_chla = EvidenceRecord(
        evidence_id="chla-stale",
        source="erddap-satellite",
        variable="chlorophyll_a",
        value=0.50,
        unit="mg/m^3",
        latitude=15.0,
        longitude=73.0,
        observed_at=FIXED_NOW - timedelta(hours=36),  # 36h old (>24h)
        retrieved_at=FIXED_NOW,
        status="valid",
    )
    null_chla = EvidenceRecord(
        evidence_id="chla-null",
        source="erddap-satellite",
        variable="chlorophyll_a",
        value=None,
        unit="mg/m^3",
        latitude=15.0,
        longitude=73.0,
        observed_at=FIXED_NOW - timedelta(hours=6),
        retrieved_at=FIXED_NOW,
        status="valid",
    )

    report = verify_environmental_linkage_freshness(
        [fresh_chla, stale_chla, null_chla],
        now=FIXED_NOW,
    )
    assert report["total_chlorophyll_records"] == 3
    assert report["fresh_count"] == 1
    assert report["stale_count"] == 2  # 1 stale by timestamp + 1 null
    assert report["null_count"] == 1
    assert report["fresh_coverage_ratio"] == round(1 / 3, 4)


# ==============================================================================
# Test 15: All 5 CMFRI Pilot Species & Landing Centers Parsing
# ==============================================================================
def test_five_pilot_species_and_landing_centers_support():
    """15. Validates all 5 CMFRI pilot species across 5 landing centers parse and resolve canonical taxonomy.

    v2.8.1: CSV rows must supply an out-of-band access_authorization_token; self-declared
    is_authorized=true alone is not sufficient.  Test fixture supplies mock tokens.
    """
    multi_center_csv = """record_identifier,source_agency,dataset_identifier,observation_method,species_name,scientific_name,latitude,longitude,spatial_uncertainty_km,landing_center_name,observed_at,catch_weight,catch_unit,effort_value,effort_unit,gear_type,is_authorized,access_authorization_token
rec-01,ICAR-CMFRI,cmfri-2024,COMMERCIAL_LANDING_STATISTIC,Indian Mackerel,Rastrelliger kanagurta,15.503,73.827,10.0,Malim Jetty,2026-10-12T06:00:00Z,250.0,kg,5.0,hours,Purse Seine,true,MOCK_AUTH_TOKEN_TEST_FIXTURE
rec-02,ICAR-CMFRI,cmfri-2024,COMMERCIAL_LANDING_STATISTIC,Indian Oil Sardine,Sardinella longiceps,16.985,73.280,12.0,Mirkarwada,2026-10-12T06:00:00Z,400.0,kg,8.0,hours,Ring Seine,true,MOCK_AUTH_TOKEN_TEST_FIXTURE
rec-03,ICAR-CMFRI,cmfri-2024,COMMERCIAL_LANDING_STATISTIC,Yellowfin Tuna,Thunnus albacares,18.915,72.825,15.0,Sasoon Docks,2026-10-12T06:00:00Z,800.0,kg,16.0,hours,Longline,true,MOCK_AUTH_TOKEN_TEST_FIXTURE
rec-04,ICAR-CMFRI,cmfri-2024,COMMERCIAL_LANDING_STATISTIC,Silver Pomfret,Pampus argenteus,14.805,74.120,8.0,Karwar Harbour,2026-10-12T06:00:00Z,180.0,kg,6.0,hours,Gillnet,true,MOCK_AUTH_TOKEN_TEST_FIXTURE
rec-05,ICAR-CMFRI,cmfri-2024,COMMERCIAL_LANDING_STATISTIC,Bombay Duck,Harpadon nehereus,12.860,74.835,10.0,Mangalore Old Port,2026-10-12T06:00:00Z,300.0,kg,6.0,hours,Dol Net,true,MOCK_AUTH_TOKEN_TEST_FIXTURE
"""
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv(multi_center_csv, is_dry_run=False, now=FIXED_NOW)

    assert summary.total_rows == 5
    assert summary.accepted_rows == 5
    assert summary.rejected_rows == 0
    assert summary.quarantined_rows == 0
    assert len(summary.imported_records) == 5

    species_resolved = {r.metadata["canonical_species"] for r in summary.imported_records}
    assert "Indian Mackerel" in species_resolved
    assert "Indian Oil Sardine" in species_resolved
    # Registry common_name is "Yellowfin Tuna" (not the stale alias "Yellowfin Tuna / Oceanic Tuna")
    assert "Yellowfin Tuna" in species_resolved
    assert "Silver Pomfret" in species_resolved
    assert "Bombay Duck" in species_resolved

    cpues = [r.metadata["cpue_kg_per_hour"] for r in summary.imported_records]
    assert cpues == [50.0, 50.0, 50.0, 30.0, 50.0]


# ==============================================================================
# Test 16: Awaiting Authorized Data Operational Store Invariance
# ==============================================================================
def test_awaiting_authorized_data_leaves_store_unchanged():
    """16. Confirms operational adapter store remains empty when awaiting authorized data."""
    importer = GroundTruthCsvImporter()
    # Query spatial fetch on untouched store
    res = importer.adapter._normalized_records
    assert len(res) == 0

    # Dry run with no file or non-existent path
    summary = importer.import_csv("", is_dry_run=True, now=FIXED_NOW)
    assert summary.accepted_rows == 0
    assert len(importer.adapter._normalized_records) == 0
