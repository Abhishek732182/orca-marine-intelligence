
from datetime import datetime, timezone
from uuid import uuid4

import httpx

from app.schemas.evidence import EvidenceRecord


class OpenMeteoMarineProvider:
    """Fetch wave-height forecasts and convert them to ORCA evidence."""

    BASE_URL = "https://marine-api.open-meteo.com/v1/marine"

    @property
    def provider_name(self) -> str:
        return "open-meteo-marine"

    async def fetch(
        self,
        *,
        latitude: float,
        longitude: float,
        observed_at: str | None = None,
    ) -> list[EvidenceRecord]:
        if not -90 <= latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")
        if not -180 <= longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "wave_height",
            "forecast_days": 1,
            "timezone": "GMT",
            "length_unit": "metric",
            "cell_selection": "sea",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            payload = response.json()

        hourly = payload.get("hourly")
        if not isinstance(hourly, dict):
            raise ValueError("Unexpected Open-Meteo hourly response")
        times = hourly.get("time", [])
        heights = hourly.get("wave_height", [])

        if not isinstance(times, list) or not isinstance(heights, list):
            raise ValueError("Unexpected Open-Meteo hourly response")

        if len(times) != len(heights):
            raise ValueError("Wave-height timestamps and values do not match")

        retrieved_at = datetime.now(timezone.utc)
        records: list[EvidenceRecord] = []

        for timestamp, height in zip(times, heights):
            if observed_at is not None and timestamp != observed_at:
                continue

            if height is None:
                continue

            observation_time = datetime.fromisoformat(
                timestamp.replace("Z", "+00:00")
            )

            if observation_time.tzinfo is None:
                observation_time = observation_time.replace(
                    tzinfo=timezone.utc
                )

            records.append(
                EvidenceRecord(
                    evidence_id=f"orca-{uuid4().hex}",
                    source=self.provider_name,
                    source_record_id=f"{timestamp}:{latitude}:{longitude}",
                    variable="wave_height",
                    value=float(height),
                    unit=payload.get("hourly_units", {}).get(
                        "wave_height", "m"
                    ),
                    latitude=float(payload.get("latitude", latitude)),
                    longitude=float(payload.get("longitude", longitude)),
                    observed_at=observation_time,
                    retrieved_at=retrieved_at,
                    status="valid",
                    quality_flags=["forecast_data"],
                    metadata={
                        "requested_latitude": latitude,
                        "requested_longitude": longitude,
                        "provider_timezone": payload.get("timezone"),
                        "model_grid_latitude": payload.get("latitude"),
                        "model_grid_longitude": payload.get("longitude"),
                    },
                )
            )

        if observed_at is not None and not records:
            raise ValueError(
                f"No wave-height value returned for timestamp {observed_at}"
            )

        return records
