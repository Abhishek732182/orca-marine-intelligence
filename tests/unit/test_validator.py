from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.evidence import EvidenceRecord, EvidenceStatus
from app.evidence.validator import validate_evidence
from app.evidence.freshness import is_stale


def make_record(
    status: EvidenceStatus = "valid",
    **overrides: object,
) -> EvidenceRecord:
    payload: dict[str, object] = {
        "evidence_id": "evidence-001",
        "source": "demo-provider",
        "variable": "sea_surface_temperature",
        "value": 28.4,
        "unit": "degC",
        "latitude": 15.0,
        "longitude": 75.0,
        "observed_at": datetime(2026, 10, 9, 10, 0, 0, tzinfo=timezone.utc),
        "retrieved_at": datetime(2026, 10, 9, 10, 5, 0, tzinfo=timezone.utc),
        "status": status,
    }
    payload.update(overrides)
    return EvidenceRecord.model_validate(payload)


def test_valid_record_has_no_issues():
    record = make_record()
    now = datetime(2026, 10, 9, 10, 10, tzinfo=timezone.utc)

    assert validate_evidence(record, now=now) == []


def test_future_retrieval_is_flagged():
    record = make_record()
    now = datetime(2026, 10, 9, 10, 0, tzinfo=timezone.utc)

    assert "retrieval_time_in_future" in validate_evidence(
        record, now=now
    )


def test_missing_observation_is_stale():
    record = make_record(observed_at=None)

    assert is_stale(record)


def test_old_observation_is_stale():
    record = make_record()
    now = datetime(2026, 10, 9, 20, 0, tzinfo=timezone.utc)

    assert is_stale(record, now=now)


def test_recent_observation_is_not_stale():
    record = make_record()
    now = datetime(2026, 10, 9, 10, 10, tzinfo=timezone.utc)

    assert not is_stale(record, now=now)


def test_naive_reference_time_is_rejected():
    record = make_record()
    now = datetime(2026, 10, 9, 10, 10)

    with pytest.raises(ValueError, match="timezone-aware"):
        validate_evidence(record, now=now)


def test_unknown_variable_is_stale_without_policy():
    record = make_record(variable="unknown_marine_variable")
    now = datetime(2026, 10, 9, 10, 10, tzinfo=timezone.utc)

    assert is_stale(record, now=now)


def test_invalid_evidence_status_is_reported():
    record = make_record(status="conflicting")
    now = datetime(2026, 10, 9, 10, 10, tzinfo=timezone.utc)

    assert "evidence_status_conflicting" in validate_evidence(
        record, now=now
    )


def test_forecast_record_allows_future_observation_without_warnings():
    """Verify that records with 'forecast_data' flag do not trigger future observation errors."""
    now = datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc)
    future_obs = datetime(2026, 10, 11, 18, 0, 0, tzinfo=timezone.utc)
    record = make_record(
        observed_at=future_obs,
        retrieved_at=now,
        quality_flags=["forecast_data"],
    )

    issues = validate_evidence(record, now=now)
    assert "observation_time_in_future" not in issues
    assert "observation_after_retrieval" not in issues
    assert issues == []


def test_non_forecast_future_observation_is_flagged():
    """Verify that standard non-forecast records with future observation time are flagged."""
    now = datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc)
    future_obs = datetime(2026, 10, 11, 18, 0, 0, tzinfo=timezone.utc)
    record = make_record(
        observed_at=future_obs,
        retrieved_at=now,
        quality_flags=[],
    )

    issues = validate_evidence(record, now=now)
    assert "observation_time_in_future" in issues
    assert "observation_after_retrieval" in issues