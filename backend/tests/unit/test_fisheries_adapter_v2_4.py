"""Deterministic Unit Tests for ORCA Fisheries v2.4: Authorized Fisheries Adapter & Quality Gates.

Verifies:
1. Valid authorized record normalization into EvidenceRecord with CPUE derivation.
2. Duplicate record rejection (spatio-temporal-species collision detection).
3. Species taxonomic identification validation against SPECIES_REGISTRY.
4. Location uncertainty threshold quarantine (> 50 km).
5. Timestamp integrity (future date rejection, voyage window bounds).
6. Missing value and sampling effort validation.
7. Unauthorized feed quarantine (status marked invalid, flagged unverified_data_feed).
8. Observation method separation (landing statistics vs surveys vs PFZ advisories).
9. Spatial vicinity querying through adapter interface.
"""

from datetime import datetime, timedelta, timezone
import pytest

from app.data_sources.biological_adapter import (
    AuthorizedFisheriesAdapter,
    BiologicalDataQualityGate,
    BiologicalObservationMethod,
    RawBiologicalFisheriesRecord,
)

FIXED_NOW = datetime(2026, 10, 12, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def adapter():
    return AuthorizedFisheriesAdapter(max_spatial_uncertainty_km=50.0)


@pytest.fixture
def valid_raw_record():
    return RawBiologicalFisheriesRecord(
        source_agency="ICAR-CMFRI",
        dataset_identifier="cmfri-arabian-sea-landings-2026",
        record_identifier="rec-goa-mackerel-001",
        observation_method=BiologicalObservationMethod.COMMERCIAL_LANDING_STATISTIC,
        species_raw_name="Indian Mackerel",
        scientific_name="Rastrelliger kanagurta",
        fao_alpha3_code="RAK",
        latitude=15.0,
        longitude=72.0,
        spatial_uncertainty_km=15.0,
        landing_center_name="Malim / Panaji",
        observed_at=datetime(2026, 10, 12, 6, 0, 0, tzinfo=timezone.utc),
        voyage_start_at=datetime(2026, 10, 12, 2, 0, 0, tzinfo=timezone.utc),
        voyage_end_at=datetime(2026, 10, 12, 8, 0, 0, tzinfo=timezone.utc),
        catch_weight_kg=450.0,
        effort_hours=6.0,
        gear_type="Trawl / Purse Seine",
        is_authorized_official_feed=True,
        access_authorization_token="MOCK_AUTH_TOKEN_CMFRI_VALIDATED",
        metadata={"catchment": "Goa Offshore neritic"},
    )


# ==============================================================================
# Test 1: Valid Authorized Record Normalization
# ==============================================================================
def test_authorized_record_normalization_success(adapter, valid_raw_record):
    """1. Normalizes authorized CMFRI record into valid EvidenceRecord with CPUE calculation."""
    ev_rec, issues = adapter.normalize_record(valid_raw_record, now=FIXED_NOW)

    assert issues == []
    assert ev_rec is not None
    assert ev_rec.status == "valid"
    assert ev_rec.variable == "fish_catch_weight"
    assert ev_rec.value == 450.0
    assert ev_rec.unit == "kg"
    assert "official_authorized_telemetry" in ev_rec.quality_flags
    assert "commercial_landing_statistic" in ev_rec.quality_flags
    assert ev_rec.metadata["canonical_species"] == "Indian Mackerel"
    assert ev_rec.metadata["cpue_kg_per_hour"] == 75.0  # 450 / 6


# ==============================================================================
# Test 2: Duplicate Record Rejection
# ==============================================================================
def test_duplicate_record_rejection(adapter, valid_raw_record):
    """2. Second identical spatio-temporal-species record must be rejected as duplicate."""
    ev1, issues1 = adapter.normalize_record(valid_raw_record, now=FIXED_NOW)
    assert issues1 == []
    assert ev1 is not None

    # Attempt to normalize duplicate record
    ev2, issues2 = adapter.normalize_record(valid_raw_record, now=FIXED_NOW)
    assert ev2 is None
    assert "duplicate_record_detected" in issues2


# ==============================================================================
# Test 3: Unsupported Species Identification Rejection
# ==============================================================================
def test_unsupported_species_identification_rejection(adapter, valid_raw_record):
    """3. Rejects records with unrecognized / unverified taxonomic identification."""
    invalid_species_record = valid_raw_record.model_copy(
        update={
            "record_identifier": "rec-goa-unknown-002",
            "species_raw_name": "Mysterious Abyssal Organism",
            "scientific_name": "Unknown species",
        }
    )

    ev, issues = adapter.normalize_record(invalid_species_record, now=FIXED_NOW)
    assert ev is None
    assert any("unsupported_or_unverified_species" in iss for iss in issues)


# ==============================================================================
# Test 4: Location Uncertainty Threshold Quarantine
# ==============================================================================
def test_location_uncertainty_threshold_quarantine(adapter, valid_raw_record):
    """4. Rejects observations whose spatial uncertainty radius exceeds 50 km."""
    high_uncertainty_record = valid_raw_record.model_copy(
        update={
            "record_identifier": "rec-goa-uncertain-003",
            "spatial_uncertainty_km": 75.0,  # Exceeds 50 km threshold
        }
    )

    ev, issues = adapter.normalize_record(high_uncertainty_record, now=FIXED_NOW)
    assert ev is None
    assert any("spatial_uncertainty_exceeds_threshold" in iss for iss in issues)


# ==============================================================================
# Test 5: Timestamp Integrity (Future Date Rejection)
# ==============================================================================
def test_timestamp_integrity_future_date_rejection(adapter, valid_raw_record):
    """5. Rejects observations timestamped in the future."""
    future_record = valid_raw_record.model_copy(
        update={
            "record_identifier": "rec-goa-future-004",
            "observed_at": FIXED_NOW + timedelta(hours=3),  # 3 hours in future
        }
    )

    ev, issues = adapter.normalize_record(future_record, now=FIXED_NOW)
    assert ev is None
    assert "observation_timestamp_in_future" in issues


# ==============================================================================
# Test 6: Voyage Interval Inconsistency Rejection
# ==============================================================================
def test_voyage_interval_inconsistency_rejection(adapter, valid_raw_record):
    """6. Rejects observations occurring outside the recorded voyage interval."""
    inconsistent_voyage_record = valid_raw_record.model_copy(
        update={
            "record_identifier": "rec-goa-voyage-005",
            "observed_at": datetime(2026, 10, 12, 10, 0, 0, tzinfo=timezone.utc),
            "voyage_start_at": datetime(2026, 10, 12, 2, 0, 0, tzinfo=timezone.utc),
            "voyage_end_at": datetime(2026, 10, 12, 8, 0, 0, tzinfo=timezone.utc),  # Ended 2h before observation
        }
    )

    ev, issues = adapter.normalize_record(inconsistent_voyage_record, now=FIXED_NOW)
    assert ev is None
    assert "observation_outside_voyage_interval" in issues


# ==============================================================================
# Test 7: Missing Catch Metric Rejection
# ==============================================================================
def test_sampling_effort_and_missing_value_rejection(adapter, valid_raw_record):
    """7. Commercial landing record with null catch weight and null biomass is rejected."""
    empty_catch_record = valid_raw_record.model_copy(
        update={
            "record_identifier": "rec-goa-empty-006",
            "catch_weight_kg": None,
            "biomass_density_kg_km2": None,
        }
    )

    ev, issues = adapter.normalize_record(empty_catch_record, now=FIXED_NOW)
    assert ev is None
    assert "missing_catch_and_biomass_metrics" in issues


# ==============================================================================
# Test 8: Unauthorized Feed Quarantined as Invalid
# ==============================================================================
def test_unauthorized_feed_quarantined_as_invalid(adapter, valid_raw_record):
    """8. Records lacking official authorization are quarantined with status invalid."""
    unauthorized_record = valid_raw_record.model_copy(
        update={
            "record_identifier": "rec-goa-unauth-007",
            "is_authorized_official_feed": False,
            "access_authorization_token": None,
        }
    )

    ev, issues = adapter.normalize_record(unauthorized_record, now=FIXED_NOW)
    assert issues == []  # Not rejected by schema, but quarantined in status
    assert ev is not None
    assert ev.status == "invalid"
    assert "unverified_data_feed" in ev.quality_flags
    assert "official_authorized_telemetry" not in ev.quality_flags


# ==============================================================================
# Test 9: Observation Method Separation
# ==============================================================================
def test_observation_method_separation(adapter, valid_raw_record):
    """9. Distinct observation methods must be tagged unambiguously without conflation."""
    research_trawl_record = valid_raw_record.model_copy(
        update={
            "record_identifier": "rec-goa-trawl-008",
            "observation_method": BiologicalObservationMethod.SCIENTIFIC_RESEARCH_TRAWL,
            "source_agency": "FSI",
        }
    )

    ev, issues = adapter.normalize_record(research_trawl_record, now=FIXED_NOW)
    assert issues == []
    assert ev is not None
    assert "scientific_research_trawl" in ev.quality_flags
    assert "commercial_landing_statistic" not in ev.quality_flags
    assert ev.source == "fisheries-fsi"


# ==============================================================================
# Test 10: Adapter Spatial Fetch Querying
# ==============================================================================
@pytest.mark.asyncio
async def test_adapter_spatial_fetch_integration(adapter, valid_raw_record):
    """10. Adapter retrieves normalized records matching spatial coordinates."""
    adapter.normalize_record(valid_raw_record, now=FIXED_NOW)

    # Coincident query at (15.0, 72.0)
    matching = await adapter.fetch(latitude=15.0, longitude=72.0)
    assert len(matching) == 1
    assert matching[0].source_record_id == "rec-goa-mackerel-001"

    # Query far away in Mumbai (18.9, 72.8)
    distant = await adapter.fetch(latitude=18.9, longitude=72.8)
    assert len(distant) == 0
