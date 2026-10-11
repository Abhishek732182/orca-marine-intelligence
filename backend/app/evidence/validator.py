from datetime import datetime, timezone

from app.schemas.evidence import EvidenceRecord


def validate_evidence(
    record: EvidenceRecord,
    *,
    now: datetime | None = None,
) -> list[str]:
    """
    Validate evidence timestamps and status.

    Returns a list of validation issues.
    An empty list means these checks passed.
    """

    issues: list[str] = []

    current_time = now or datetime.now(timezone.utc)

    # The reference time must include a timezone.
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    # Retrieval must not occur in the future.
    if record.retrieved_at > current_time:
        issues.append("retrieval_time_in_future")

    # Check observation timestamp consistency.
    if record.observed_at is not None:
        if record.observed_at > current_time:
            issues.append("observation_time_in_future")

        if record.observed_at > record.retrieved_at:
            issues.append("observation_after_retrieval")

    # Preserve the existing status; do not silently mark evidence valid.
    if record.status != "valid":
        issues.append(f"evidence_status_{record.status}")

    return issues

