from datetime import datetime, timedelta, timezone

from app.schemas.evidence import EvidenceRecord


# Initial engineering defaults and documented marine validity windows.
DEFAULT_MAX_AGE = {
    "sea_surface_temperature": timedelta(hours=6),
    "wave_height": timedelta(hours=3),
    "wind_speed": timedelta(hours=3),
    "chlorophyll_a": timedelta(hours=24),  # Standard 24h satellite ocean-color composite
    "fish_biomass": timedelta(days=7),     # In-situ fisheries survey validity window
}


def is_stale(
    record: EvidenceRecord,
    *,
    now: datetime | None = None,
    allow_forecast: bool | None = None,
) -> bool:
    if record.observed_at is None:
        return True

    current_time = now or datetime.now(timezone.utc)

    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    is_forecast = (
        allow_forecast
        if allow_forecast is not None
        else ("forecast_data" in (record.quality_flags or []))
    )

    if record.observed_at > current_time:
        return not is_forecast

    max_age = DEFAULT_MAX_AGE.get(record.variable)

    # Unknown variables need an explicit policy before freshness is asserted.
    if max_age is None:
        return True

    return current_time - record.observed_at > max_age