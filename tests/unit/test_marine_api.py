from datetime import datetime, timezone
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes import marine
from app.schemas.evidence import EvidenceRecord


client = TestClient(app)


def test_wave_height_endpoint_returns_forecast(monkeypatch):
    async def fake_fetch(*, latitude, longitude):
        return [
            EvidenceRecord(
                evidence_id="test-wave-001",
                source="open-meteo-marine",
                variable="wave_height",
                value=0.94,
                unit="m",
                latitude=15.04,
                longitude=71.96,
                observed_at=datetime(2026, 10, 9, 0, 0, 0, tzinfo=timezone.utc),
                retrieved_at=datetime(2026, 10, 9, 18, 29, 0, tzinfo=timezone.utc),
                status="valid",
                quality_flags=["forecast_data"],
            )
        ]

    monkeypatch.setattr(marine.provider, "fetch", fake_fetch)

    response = client.get(
        "/api/marine/wave-height",
        params={
            "latitude": 15.0,
            "longitude": 72.0,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["source"] == "open-meteo-marine"
    assert body["data_available"] is True
    assert body["count"] == 1
    assert body["records"][0]["variable"] == "wave_height"
    assert body["records"][0]["value"] == 0.94
    assert body["records"][0]["unit"] == "m"
    assert "forecast_data" in body["records"][0]["quality_flags"]


def test_wave_height_endpoint_rejects_invalid_coordinates():
    response = client.get(
        "/api/marine/wave-height",
        params={
            "latitude": 100,
            "longitude": 72,
        },
    )

    assert response.status_code == 422


def test_wave_height_endpoint_handles_provider_failure(monkeypatch):
    async def failing_fetch(*, latitude, longitude):
        raise httpx.ConnectError("Simulated connection failure")

    monkeypatch.setattr(marine.provider, "fetch", failing_fetch)

    response = client.get(
        "/api/marine/wave-height",
        params={
            "latitude": 15.0,
            "longitude": 72.0,
        },
    )

    assert response.status_code == 502
    assert "temporarily unavailable" in response.json()["detail"]
