
from datetime import timezone

import httpx
import pytest

from app.data_sources.open_meteo_marine import (
    OpenMeteoMarineProvider,
)


@pytest.mark.asyncio
async def test_fetch_converts_api_response_to_evidence(monkeypatch):
    async def mock_get(self, url, **kwargs):
        return httpx.Response(
            200,
            json={
                "latitude": 15.0,
                "longitude": 75.0,
                "timezone": "GMT",
                "hourly": {
                    "time": [
                        "2026-10-09T10:00",
                        "2026-10-09T11:00",
                    ],
                    "wave_height": [1.2, 1.5],
                },
                "hourly_units": {"wave_height": "m"},
            },
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    provider = OpenMeteoMarineProvider()
    records = await provider.fetch(latitude=15.0, longitude=75.0)

    assert len(records) == 2
    assert records[0].variable == "wave_height"
    assert records[0].value == 1.2
    assert records[0].unit == "m"
    assert records[0].observed_at is not None
    assert records[0].observed_at.tzinfo is not None
    assert records[0].retrieved_at.tzinfo == timezone.utc
    assert "forecast_data" in records[0].quality_flags


@pytest.mark.asyncio
async def test_invalid_latitude_is_rejected():
    provider = OpenMeteoMarineProvider()

    with pytest.raises(ValueError, match="latitude"):
        await provider.fetch(latitude=100, longitude=75)


@pytest.mark.asyncio
async def test_invalid_longitude_is_rejected():
    provider = OpenMeteoMarineProvider()

    with pytest.raises(ValueError, match="longitude"):
        await provider.fetch(latitude=15, longitude=200)


@pytest.mark.asyncio
async def test_fetch_rejects_malformed_hourly_payload(monkeypatch):
    """Verify provider raises ValueError when Open-Meteo returns non-list hourly data."""
    async def mock_get(self, url, **kwargs):
        return httpx.Response(
            200,
            json={"latitude": 15.0, "longitude": 75.0, "hourly": "invalid_structure"},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    provider = OpenMeteoMarineProvider()
    with pytest.raises(ValueError, match="Unexpected Open-Meteo hourly response"):
        await provider.fetch(latitude=15.0, longitude=75.0)


@pytest.mark.asyncio
async def test_fetch_rejects_mismatched_timestamps_and_values(monkeypatch):
    """Verify provider raises ValueError when timestamps and values counts diverge."""
    async def mock_get(self, url, **kwargs):
        return httpx.Response(
            200,
            json={
                "latitude": 15.0,
                "longitude": 75.0,
                "hourly": {
                    "time": ["2026-10-09T10:00", "2026-10-09T11:00"],
                    "wave_height": [1.2],
                },
            },
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    provider = OpenMeteoMarineProvider()
    with pytest.raises(ValueError, match="timestamps and values do not match"):
        await provider.fetch(latitude=15.0, longitude=75.0)


@pytest.mark.asyncio
async def test_fetch_raises_on_http_error(monkeypatch):
    """Verify provider raises HTTPStatusError when Open-Meteo returns server failure."""
    async def mock_get(self, url, **kwargs):
        return httpx.Response(
            500,
            text="Internal Server Error",
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    provider = OpenMeteoMarineProvider()
    with pytest.raises(httpx.HTTPStatusError):
        await provider.fetch(latitude=15.0, longitude=75.0)
