from datetime import datetime, timezone
from typing_extensions import TypedDict

import pytest
from pydantic import ValidationError

from app.schemas.evidence import EvidenceRecord, EvidenceStatus


class ValidPayloadDict(TypedDict):
    evidence_id: str
    source: str
    source_record_id: str | None
    variable: str
    value: float | str | bool | None
    unit: str | None
    latitude: float | None
    longitude: float | None
    depth_m: float | None
    observed_at: datetime | None
    retrieved_at: datetime
    status: EvidenceStatus
    quality_flags: list[str]
    metadata: dict[str, object]


def valid_payload() -> ValidPayloadDict:
    return {
        "evidence_id": "evidence-001",
        "source": "demo-provider",
        "source_record_id": "record-001",
        "variable": "sea_surface_temperature",
        "value": 28.4,
        "unit": "degC",
        "latitude": 15.0,
        "longitude": 75.0,
        "depth_m": 0.0,
        "observed_at": datetime(2026, 10, 9, 10, 0, 0, tzinfo=timezone.utc),
        "retrieved_at": datetime(2026, 10, 9, 10, 5, 0, tzinfo=timezone.utc),
        "status": "valid",
        "quality_flags": [],
        "metadata": {},
    }


def test_valid_evidence_record():
    record = EvidenceRecord(**valid_payload())

    assert record.variable == "sea_surface_temperature"
    assert record.value == 28.4
    assert record.status == "valid"


def test_rejects_invalid_latitude():
    payload = valid_payload()
    payload["latitude"] = 95

    with pytest.raises(ValidationError):
        EvidenceRecord(**payload)


def test_rejects_invalid_longitude():
    payload = valid_payload()
    payload["longitude"] = 190

    with pytest.raises(ValidationError):
        EvidenceRecord(**payload)


def test_rejects_naive_timestamp():
    payload = valid_payload()
    payload["retrieved_at"] = datetime(2026, 10, 9, 10, 5, 0)

    with pytest.raises(ValidationError):
        EvidenceRecord(**payload)


def test_rejects_unknown_fields():
    payload: dict[str, object] = dict(valid_payload())
    payload["unknown_field"] = "unexpected"

    with pytest.raises(ValidationError):
        EvidenceRecord.model_validate(payload)


def test_allows_missing_observation_time():
    payload = valid_payload()
    payload["observed_at"] = None
    payload["status"] = "missing"

    record = EvidenceRecord(**payload)

    assert record.observed_at is None
    assert record.status == "missing"