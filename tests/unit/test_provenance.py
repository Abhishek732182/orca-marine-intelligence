from datetime import datetime, timezone

from app.schemas.evidence import EvidenceRecord
from app.evidence.provenance import create_provenance


def make_evidence() -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id="evidence-001",
        source="demo-provider",
        source_record_id="record-123",
        variable="sea_surface_temperature",
        value=28.4,
        unit="degC",
        latitude=15.0,
        longitude=75.0,
        observed_at=datetime(2026, 10, 9, 10, 0, 0, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 10, 9, 10, 5, 0, tzinfo=timezone.utc),
        status="valid",
    )


def test_provenance_preserves_source_identity():
    provenance = create_provenance(make_evidence())

    assert provenance.evidence_id == "evidence-001"
    assert provenance.source == "demo-provider"
    assert provenance.source_record_id == "record-123"


def test_provenance_records_transformations():
    provenance = create_provenance(
        make_evidence(),
        transformations=["unit_normalization"],
        metadata={"mapper_version": "1"},
    )

    assert provenance.transformations == ["unit_normalization"]
    assert provenance.metadata["mapper_version"] == "1"


def test_provenance_does_not_modify_evidence():
    evidence = make_evidence()
    original_value = evidence.value

    create_provenance(
        evidence,
        transformations=["validated"],
    )

    assert evidence.value == original_value