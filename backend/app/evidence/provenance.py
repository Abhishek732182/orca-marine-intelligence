from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.evidence import EvidenceRecord


class ProvenanceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    source: str
    source_record_id: str | None = None
    retrieved_at: datetime

    transformations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


def create_provenance(
    evidence: EvidenceRecord,
    *,
    transformations: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> ProvenanceRecord:
    """Create a provenance record for a validated evidence record."""

    return ProvenanceRecord(
        evidence_id=evidence.evidence_id,
        source=evidence.source,
        source_record_id=evidence.source_record_id,
        retrieved_at=evidence.retrieved_at,
        transformations=transformations or [],
        metadata=metadata or {},
    )