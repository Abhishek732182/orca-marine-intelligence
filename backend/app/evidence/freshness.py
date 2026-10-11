from datetime import datetime, timedelta, timezone

from app.schemas.evidence import EvidenceRecord


# Initial engineering defaults, not scientifically validated thresholds.
DEFAULT_MAX_AGE = {
    "sea_surface_temperature": timedelta(hours=6),
    "wave_height": timedelta(hours=3),
    "wind_speed": timedelta(hours=3),
}


def is_stale(
    record: EvidenceRecord,
    *,
    now: datetime | None = None,
) -> bool:
    if record.observed_at is None:
        return True

    current_time = now or datetime.now(timezone.utc)

    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    if record.observed_at > current_time:
        return True

    max_age = DEFAULT_MAX_AGE.get(record.variable)

    # Unknown variables need an explicit policy before freshness is asserted.
    if max_age is None:
        return True

    return current_time - record.observed_at > max_age