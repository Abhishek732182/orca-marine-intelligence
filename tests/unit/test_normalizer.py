from typing import cast

import pytest
from pydantic import ValidationError

from app.evidence.normalizer import normalize_evidence


def valid_payload():
    return {
        "evidence_id": "evidence-001",
        "source": "demo-provider",
        "variable": "sea_surface_temperature",
        "value": 28.4,
        "unit": "degC",
        "latitude": 15.0,
        "longitude": 75.0,
        "observed_at": "2026-10-09T10:00:00Z",
        "retrieved_at": "2026-10-09T10:05:00Z",
        "status": "valid",
    }


def test_normalizes_valid_payload():
    record = normalize_evidence(valid_payload())

    assert record.evidence_id == "evidence-001"
    assert record.value == 28.4
    assert record.source == "demo-provider"


def test_rejects_missing_required_field():
    payload = valid_payload()
    del payload["source"]

    with pytest.raises(ValueError, match="Missing required fields"):
        normalize_evidence(payload)


def test_rejects_invalid_coordinates():
    payload = valid_payload()
    payload["latitude"] = 100

    with pytest.raises(ValidationError):
        normalize_evidence(payload)


def test_rejects_unexpected_fields():
    payload = valid_payload()
    payload["unrecognized"] = True

    with pytest.raises(ValidationError):
        normalize_evidence(payload)


def test_rejects_non_dictionary_payload():
    with pytest.raises(TypeError, match="dictionary"):
        normalize_evidence(cast(dict[str, object], []))