from typing import Any

from pydantic import ValidationError

from app.schemas.evidence import EvidenceRecord


def normalize_evidence(
    payload: dict[str, Any],
) -> EvidenceRecord:
    """Validate and normalize a canonical evidence payload.

    Provider-specific field mapping belongs in each provider's mapper.
    This function does not guess units, timestamps, or coordinates.
    """

    if not isinstance(payload, dict):
        raise TypeError("payload must be a dictionary")

    required_fields = {
        "evidence_id",
        "source",
        "variable",
        "value",
        "retrieved_at",
        "status",
    }

    missing = required_fields - payload.keys()
    if missing:
        fields = ", ".join(sorted(missing))
        raise ValueError(f"Missing required fields: {fields}")

    try:
        return EvidenceRecord.model_validate(payload)
    except ValidationError:
        # Preserve Pydantic's field-level validation details.
        raise