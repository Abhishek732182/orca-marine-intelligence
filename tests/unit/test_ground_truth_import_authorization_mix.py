import pytest
from datetime import datetime, timezone

from app.data_sources.ground_truth_import import GroundTruthCsvImporter

FIXED_NOW = datetime(2026, 10, 12, 12, 0, 0, tzinfo=timezone.utc)

SAMPLE_MIXED_CSV = """record_identifier,source_agency,dataset_identifier,observation_method,species_name,scientific_name,latitude,longitude,spatial_uncertainty_km,landing_center_name,observed_at,voyage_start_at,voyage_end_at,catch_weight,catch_unit,effort_value,effort_unit,gear_type,is_authorized,access_authorization_token
rec-auth-001,ICAR-CMFRI,cmfri-2024,COMMERCIAL_LANDING_STATISTIC,Indian Mackerel,Rastrelliger kanagurta,15.503,73.827,10.0,Malim Jetty,2026-10-12T06:00:00Z,2026-10-12T01:00:00Z,2026-10-12T08:00:00Z,300.0,kg,5.0,hours,Purse Seine,true,MOCK_TOKEN_AUTH
rec-unauth-001,ICAR-CMFRI,cmfri-2024,COMMERCIAL_LANDING_STATISTIC,Indian Mackerel,Rastrelliger kanagurta,16.503,74.827,10.0,Malim Jetty,2026-10-12T07:00:00Z,2026-10-12T02:00:00Z,2026-10-12T09:00:00Z,200.0,kg,4.0,hours,Purse Seine,false,
"""


def test_import_mixed_authorization():
    """Verify mixed batch: authorized row is accepted, unauthorized row is quarantined, and only authorized row enters operational store."""
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv(SAMPLE_MIXED_CSV, is_dry_run=False, now=FIXED_NOW)

    assert summary.total_rows == 2
    assert summary.accepted_rows == 1
    assert summary.quarantined_rows == 1
    assert summary.rejected_rows == 0
    # Authorized row was accepted, so dataset is marked authorized
    assert summary.is_authorized_dataset is True
    assert len(summary.imported_records) == 1
    rec = summary.imported_records[0]
    assert rec.metadata["is_authorized"] is True
    assert rec.metadata["canonical_species"] == "Indian Mackerel"
    # Ensure operational biological store contains only the valid authorized record
    assert len(importer.adapter._normalized_records) == 1
    assert importer.adapter._normalized_records[0].source_record_id == "rec-auth-001"


def test_import_no_authorized_rows():
    """Verify batch with only unauthorized rows: records are quarantined, not committed to operational store."""
    csv_no_auth = """record_identifier,source_agency,dataset_identifier,observation_method,species_name,scientific_name,latitude,longitude,spatial_uncertainty_km,landing_center_name,observed_at,voyage_start_at,voyage_end_at,catch_weight,catch_unit,effort_value,effort_unit,gear_type,is_authorized,access_authorization_token
rec-unauth-001,ICAR-CMFRI,cmfri-2024,COMMERCIAL_LANDING_STATISTIC,Indian Mackerel,Rastrelliger kanagurta,15.503,73.827,10.0,Malim Jetty,2026-10-12T06:00:00Z,2026-10-12T01:00:00Z,2026-10-12T08:00:00Z,300.0,kg,5.0,hours,Purse Seine,false,
"""
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv(csv_no_auth, is_dry_run=False, now=FIXED_NOW)

    assert summary.total_rows == 1
    assert summary.accepted_rows == 0
    assert summary.quarantined_rows == 1
    assert summary.rejected_rows == 0
    assert summary.is_authorized_dataset is False
    assert len(summary.imported_records) == 0
    # Operational biological store must remain empty
    assert len(importer.adapter._normalized_records) == 0


def test_import_self_declared_authorization_without_token_rejected():
    """Verify self-declared authorization bypass attempt (is_authorized=true without token) is rejected and does not mark dataset authorized."""
    csv_self_declared = """record_identifier,source_agency,dataset_identifier,observation_method,species_name,scientific_name,latitude,longitude,spatial_uncertainty_km,landing_center_name,observed_at,voyage_start_at,voyage_end_at,catch_weight,catch_unit,effort_value,effort_unit,gear_type,is_authorized,access_authorization_token
rec-fake-001,ICAR-CMFRI,cmfri-2024,COMMERCIAL_LANDING_STATISTIC,Indian Mackerel,Rastrelliger kanagurta,15.503,73.827,10.0,Malim Jetty,2026-10-12T06:00:00Z,2026-10-12T01:00:00Z,2026-10-12T08:00:00Z,300.0,kg,5.0,hours,Purse Seine,true,
"""
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv(csv_self_declared, is_dry_run=False, now=FIXED_NOW)

    assert summary.total_rows == 1
    assert summary.accepted_rows == 0
    assert summary.rejected_rows == 1
    assert summary.quarantined_rows == 0
    # CRITICAL: Dataset must NOT be marked authorized
    assert summary.is_authorized_dataset is False
    assert len(summary.imported_records) == 0
    assert len(importer.adapter._normalized_records) == 0
    assert "self_declared_authorization_no_external_token" in summary.rejection_reasons_by_row[1]


def test_import_duplicate_batch_idempotence():
    """Verify duplicate import of identical file is skipped idempotently without re-inserting."""
    importer = GroundTruthCsvImporter()
    summary1 = importer.import_csv(SAMPLE_MIXED_CSV, is_dry_run=False, now=FIXED_NOW)
    assert summary1.accepted_rows == 1
    assert len(importer.adapter._normalized_records) == 1

    summary2 = importer.import_csv(SAMPLE_MIXED_CSV, is_dry_run=False, now=FIXED_NOW)
    assert summary2.is_idempotent_reimport is True
    assert summary2.accepted_rows == 0
    # Store count remains unchanged
    assert len(importer.adapter._normalized_records) == 1
    assert summary2.store_count_before == 1
    assert summary2.store_count_after == 1


def test_import_empty_batch_leaves_store_unchanged():
    """Verify empty batch leaves biological store untouched with is_authorized_dataset=False."""
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv("   ", is_dry_run=False, now=FIXED_NOW)
    assert summary.total_rows == 0
    assert summary.accepted_rows == 0
    assert summary.is_authorized_dataset is False
    assert len(importer.adapter._normalized_records) == 0


def test_import_whitespace_token_rejected_as_self_declared():
    """Verify whitespace-only token is rejected and cannot bypass authorization gate."""
    csv_whitespace_token = """record_identifier,source_agency,dataset_identifier,observation_method,species_name,scientific_name,latitude,longitude,spatial_uncertainty_km,landing_center_name,observed_at,voyage_start_at,voyage_end_at,catch_weight,catch_unit,effort_value,effort_unit,gear_type,is_authorized,access_authorization_token
rec-ws-001,ICAR-CMFRI,cmfri-2024,COMMERCIAL_LANDING_STATISTIC,Indian Mackerel,Rastrelliger kanagurta,15.503,73.827,10.0,Malim Jetty,2026-10-12T06:00:00Z,2026-10-12T01:00:00Z,2026-10-12T08:00:00Z,300.0,kg,5.0,hours,Purse Seine,true,   
"""
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv(csv_whitespace_token, is_dry_run=False, now=FIXED_NOW)
    assert summary.accepted_rows == 0
    assert summary.rejected_rows == 1
    assert summary.is_authorized_dataset is False
    assert len(importer.adapter._normalized_records) == 0
    assert "self_declared_authorization_no_external_token" in summary.rejection_reasons_by_row[1]


def test_import_failed_batch_leaves_zero_partial_commits():
    """Verify that a batch with all rejected rows leaves zero partial commits in the operational store."""
    csv_all_rejected = """record_identifier,source_agency,dataset_identifier,observation_method,species_name,scientific_name,latitude,longitude,spatial_uncertainty_km,landing_center_name,observed_at,voyage_start_at,voyage_end_at,catch_weight,catch_unit,effort_value,effort_unit,gear_type,is_authorized,access_authorization_token
rec-rej-001,ICAR-CMFRI,cmfri-2024,COMMERCIAL_LANDING_STATISTIC,Unknown Fish,Taxon nonexistus,15.503,73.827,10.0,Malim Jetty,2026-10-12T06:00:00Z,2026-10-12T01:00:00Z,2026-10-12T08:00:00Z,300.0,kg,5.0,hours,Purse Seine,true,VALID_TOKEN
rec-rej-002,ICAR-CMFRI,cmfri-2024,COMMERCIAL_LANDING_STATISTIC,Indian Mackerel,Rastrelliger kanagurta,99.999,73.827,10.0,Malim Jetty,2026-10-12T06:00:00Z,2026-10-12T01:00:00Z,2026-10-12T08:00:00Z,300.0,kg,5.0,hours,Purse Seine,true,VALID_TOKEN
"""
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv(csv_all_rejected, is_dry_run=False, now=FIXED_NOW)
    assert summary.total_rows == 2
    assert summary.accepted_rows == 0
    assert summary.rejected_rows == 2
    assert summary.is_authorized_dataset is False
    assert len(summary.imported_records) == 0
    assert len(importer.adapter._normalized_records) == 0


def test_failure_during_commit_sequence_triggers_rollback():
    """Verify failure during the commit sequence triggers complete rollback of records, signatures, and checksums."""
    importer = GroundTruthCsvImporter()
    initial_sigs = set(importer.adapter.quality_gate.seen_signatures)
    initial_recs = list(importer.adapter._normalized_records)
    initial_checksums = set(importer.imported_file_checksums)

    # Use a list subclass that raises on extend to simulate commit sequence failure
    class FaultyRecordStore(list):
        def extend(self, iterable):
            raise RuntimeError("Simulated database failure during batch commit sequence")

    importer.adapter._normalized_records = FaultyRecordStore(initial_recs)

    with pytest.raises(RuntimeError, match="Simulated database failure during batch commit sequence"):
        importer.import_csv(SAMPLE_MIXED_CSV, is_dry_run=False, now=FIXED_NOW)

    # Verify rollback invariants: zero partial mutation
    assert list(importer.adapter._normalized_records) == initial_recs
    assert importer.adapter.quality_gate.seen_signatures == initial_sigs
    assert importer.imported_file_checksums == initial_checksums


def test_dry_run_restores_all_mutable_state():
    """Verify dry run restores all mutable state and does not block subsequent actual import."""
    importer = GroundTruthCsvImporter()
    initial_sigs = set(importer.adapter.quality_gate.seen_signatures)
    initial_recs = list(importer.adapter._normalized_records)
    initial_checksums = set(importer.imported_file_checksums)

    summary_dry = importer.import_csv(SAMPLE_MIXED_CSV, is_dry_run=True, now=FIXED_NOW)
    assert summary_dry.is_dry_run is True
    assert summary_dry.accepted_rows == 1
    assert len(summary_dry.imported_records) == 0

    # Verify all mutable state restored
    assert importer.adapter._normalized_records == initial_recs
    assert importer.adapter.quality_gate.seen_signatures == initial_sigs
    assert importer.imported_file_checksums == initial_checksums

    # Subsequent non-dry-run import must succeed without duplicate blocking
    summary_real = importer.import_csv(SAMPLE_MIXED_CSV, is_dry_run=False, now=FIXED_NOW)
    assert summary_real.accepted_rows == 1
    assert len(importer.adapter._normalized_records) == 1
    assert len(importer.imported_file_checksums) == 1


def test_mixed_batch_under_partial_acceptance_policy():
    """Verify mixed authorized/unauthorized/invalid batch under documented partial-acceptance policy."""
    three_row_csv = """record_identifier,source_agency,dataset_identifier,observation_method,species_name,scientific_name,latitude,longitude,spatial_uncertainty_km,landing_center_name,observed_at,voyage_start_at,voyage_end_at,catch_weight,catch_unit,effort_value,effort_unit,gear_type,is_authorized,access_authorization_token
rec-01,ICAR-CMFRI,cmfri-2024,COMMERCIAL_LANDING_STATISTIC,Indian Mackerel,Rastrelliger kanagurta,15.503,73.827,10.0,Malim Jetty,2026-10-12T06:00:00Z,2026-10-12T01:00:00Z,2026-10-12T08:00:00Z,300.0,kg,5.0,hours,Purse Seine,true,AUTH_TOKEN_VALID
rec-02,ICAR-CMFRI,cmfri-2024,COMMERCIAL_LANDING_STATISTIC,Indian Mackerel,Rastrelliger kanagurta,16.503,74.827,10.0,Malim Jetty,2026-10-12T07:00:00Z,2026-10-12T02:00:00Z,2026-10-12T09:00:00Z,200.0,kg,4.0,hours,Purse Seine,false,
rec-03,ICAR-CMFRI,cmfri-2024,COMMERCIAL_LANDING_STATISTIC,Fictional Mythical Taxon,Mythicus nonexistus,17.503,75.827,10.0,Malim Jetty,2026-10-12T08:00:00Z,2026-10-12T03:00:00Z,2026-10-12T10:00:00Z,100.0,kg,2.0,hours,Purse Seine,true,AUTH_TOKEN_VALID
"""
    importer = GroundTruthCsvImporter()
    summary = importer.import_csv(three_row_csv, is_dry_run=False, now=FIXED_NOW)

    assert summary.total_rows == 3
    assert summary.accepted_rows == 1
    assert summary.quarantined_rows == 1
    assert summary.rejected_rows == 1
    assert summary.is_authorized_dataset is True

    # Operational store has ONLY the 1 valid authorized row
    assert len(importer.adapter._normalized_records) == 1
    assert importer.adapter._normalized_records[0].source_record_id == "rec-01"

    # Deduplication signatures only retain the accepted row, not the quarantined or rejected rows
    assert len(importer.adapter.quality_gate.seen_signatures) == 1


def test_concurrent_imports_are_serialized_safely():
    """Verify concurrent import calls on a shared importer are safely serialized without state corruption."""
    import concurrent.futures

    importer = GroundTruthCsvImporter()

    def generate_csv(row_id: int) -> str:
        return f"""record_identifier,source_agency,dataset_identifier,observation_method,species_name,scientific_name,latitude,longitude,spatial_uncertainty_km,landing_center_name,observed_at,voyage_start_at,voyage_end_at,catch_weight,catch_unit,effort_value,effort_unit,gear_type,is_authorized,access_authorization_token
rec-{row_id},ICAR-CMFRI,cmfri-2024,COMMERCIAL_LANDING_STATISTIC,Indian Mackerel,Rastrelliger kanagurta,15.{row_id:03d},73.827,10.0,Malim Jetty,2026-10-12T06:00:00Z,2026-10-12T01:00:00Z,2026-10-12T08:00:00Z,300.0,kg,5.0,hours,Purse Seine,true,AUTH_TOKEN_VALID
"""

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(importer.import_csv, generate_csv(i), is_dry_run=False, now=FIXED_NOW)
            for i in range(1, 6)
        ]
        results = [f.result() for f in futures]

    assert len(results) == 5
    assert all(r.accepted_rows == 1 for r in results)
    # Operational store has all 5 records without drop or race condition
    assert len(importer.adapter._normalized_records) == 5
    assert len(importer.adapter.quality_gate.seen_signatures) == 5





