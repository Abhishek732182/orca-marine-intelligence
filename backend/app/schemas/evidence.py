from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


EvidenceStatus = Literal[
    "valid",
    "stale",
    "missing",
    "invalid",
    "conflicting",
]


class EvidenceRecord(BaseModel):
    """Standardized record for a marine observation or finding."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    source_record_id: str | None = None

    variable: str = Field(min_length=1)
    value: float | str | bool | None
    unit: str | None = None

    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    depth_m: float | None = Field(default=None, ge=0)

    observed_at: datetime | None = None
    retrieved_at: datetime

    status: EvidenceStatus
    quality_flags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_timestamps(self):
        timestamps = [self.retrieved_at]
        if self.observed_at is not None:
            timestamps.append(self.observed_at)

        for timestamp in timestamps:
            if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                raise ValueError(
                    "Timestamps must include a timezone."
                )

        return self