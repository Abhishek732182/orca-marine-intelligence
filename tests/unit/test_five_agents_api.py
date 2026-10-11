"""API integration tests for all five independent ORCA agents."""

from datetime import datetime, timezone
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.api.routes.agents import weather, ocean, fishing_zone, safety_risk
from app.schemas.evidence import EvidenceRecord

client = TestClient(app)


def test_all_five_agent_routes_registered():
    """Verify all 5 agent routes are registered in FastAPI OpenAPI schema."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]

    assert "/api/agents/weather/analyze" in paths
    assert "/api/agents/ocean/analyze" in paths
    assert "/api/agents/fishing-zone/analyze" in paths
    assert "/api/agents/route/analyze" in paths
    assert "/api/agents/safety-risk/analyze" in paths
    assert "/api/agents/orchestrator/analyze" in paths
    assert "/api/agents/assistant/chat" in paths
    assert "/api/agents/assistant/chat/stream" in paths
    assert "/api/agents/assistant/approve" in paths

    # Verify preserved endpoints
    assert "/api/orca/analyze" in paths
    assert "/api/marine/wave-height" in paths
    assert "/api/health" in paths
    assert "/health" in paths


def test_weather_endpoint_valid(monkeypatch):
    """Test POST /api/agents/weather/analyze."""
    async def fake_fetch(*, latitude, longitude, forecast_days):
        return {
            "latitude": latitude,
            "longitude": longitude,
            "current_weather": {
                "time": "2026-10-11T12:00",
                "temperature": 27.5,
                "windspeed": 18.5,
                "winddirection": 220.0,
                "weathercode": 1,
            },
            "hourly": {
                "time": ["2026-10-11T12:00"],
                "temperature_2m": [27.5],
                "wind_speed_10m": [18.5],
                "wind_direction_10m": [220.0],
                "precipitation": [0.0],
            },
        }

    monkeypatch.setattr(weather.agent.provider, "fetch_weather", fake_fetch)

    res = client.post(
        "/api/agents/weather/analyze",
        json={"latitude": 15.0, "longitude": 72.0, "location_name": "Offshore Goa"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["agent"] == "Weather Agent"
    assert data["status"] == "success"
    assert data["observations"]["temperature_c"] == 27.5


def test_ocean_endpoint_valid(monkeypatch):
    """Test POST /api/agents/ocean/analyze."""
    now_utc = datetime.now(timezone.utc)

    async def fake_fetch(*, latitude, longitude):
        return [
            EvidenceRecord(
                evidence_id="ev-101",
                source="open-meteo-marine",
                source_record_id="rec-101",
                variable="wave_height",
                value=1.5,
                unit="m",
                latitude=latitude,
                longitude=longitude,
                observed_at=now_utc,
                retrieved_at=now_utc,
                status="valid",
            )
        ]

    monkeypatch.setattr(ocean.agent.provider, "fetch", fake_fetch)

    res = client.post(
        "/api/agents/ocean/analyze",
        json={"latitude": 15.0, "longitude": 72.0, "location_name": "Goa Offshore"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["agent"] == "Ocean Agent"
    assert data["status"] == "success"
    assert data["observations"]["avg_wave_height_m"] == 1.5


def test_fishing_zone_endpoint_valid(monkeypatch):
    """Test POST /api/agents/fishing-zone/analyze."""
    now_utc = datetime.now(timezone.utc)

    async def fake_fetch(*, latitude, longitude):
        return [
            EvidenceRecord(
                evidence_id="ev-201",
                source="open-meteo-marine",
                source_record_id="rec-201",
                variable="wave_height",
                value=1.1,
                unit="m",
                latitude=latitude,
                longitude=longitude,
                observed_at=now_utc,
                retrieved_at=now_utc,
                status="valid",
            )
        ]

    monkeypatch.setattr(fishing_zone.agent.provider, "fetch", fake_fetch)

    res = client.post(
        "/api/agents/fishing-zone/analyze",
        json={"latitude": 15.0, "longitude": 72.0, "target_species": "Mackerel"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["agent"] == "Fishing Zone Agent"
    # Adheres to: returns insufficient_evidence when direct fish telemetry is unavailable
    assert data["status"] == "insufficient_evidence"
    assert data["analysis"]["operational_feasibility"] == "FAVORABLE"


def test_route_endpoint_valid():
    """Test POST /api/agents/route/analyze."""
    res = client.post(
        "/api/agents/route/analyze",
        json={
            "origin_latitude": 18.9,
            "origin_longitude": 72.8,
            "origin_name": "Mumbai Port",
            "destination_latitude": 15.4,
            "destination_longitude": 73.8,
            "destination_name": "Mormugao Port",
            "vessel_speed_knots": 14.0,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["agent"] == "Route Agent"
    assert data["status"] == "success"
    assert data["observations"]["total_distance_nm"] > 0
    assert data["analysis"]["navigation_type"] == "geodesic_straight_line"


def test_safety_risk_endpoint_valid(monkeypatch):
    """Test POST /api/agents/safety-risk/analyze."""
    res = client.post(
        "/api/agents/safety-risk/analyze",
        json={
            "latitude": 15.0,
            "longitude": 72.0,
            "vessel_type": "small_craft",
            "wave_height_m": 1.2,
            "wind_speed_knots": 14.0,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["agent"] == "Safety/Risk Agent"
    assert data["status"] == "success"
    assert data["analysis"]["risk_category"] == "LOW"


def test_invalid_coordinates_rejected_across_agents():
    """Verify 422 Unprocessable Entity on out-of-range coordinates."""
    # Latitude > 90
    assert client.post("/api/agents/ocean/analyze", json={"latitude": 100.0, "longitude": 72.0}).status_code == 422
    assert client.post("/api/agents/weather/analyze", json={"latitude": 100.0, "longitude": 72.0}).status_code == 422
    assert client.post("/api/agents/fishing-zone/analyze", json={"latitude": 100.0, "longitude": 72.0}).status_code == 422
    assert client.post("/api/agents/safety-risk/analyze", json={"latitude": 100.0, "longitude": 72.0}).status_code == 422
    assert client.post(
        "/api/agents/route/analyze",
        json={"origin_latitude": 100.0, "origin_longitude": 72.0, "destination_latitude": 15.0, "destination_longitude": 72.0},
    ).status_code == 422


def test_malformed_requests_rejected():
    """Verify 422 on malformed or empty payloads."""
    assert client.post("/api/agents/ocean/analyze", json={}).status_code == 422
    assert client.post("/api/agents/route/analyze", json={"origin_latitude": "not-a-number"}).status_code == 422


def test_api_endpoints_missing_evidence_handling(monkeypatch):
    """Verify API endpoints gracefully report insufficient_evidence when data is missing."""
    # 1. Ocean agent on land returns insufficient_evidence
    async def empty_marine_fetch(*, latitude, longitude):
        return []

    monkeypatch.setattr(ocean.agent.provider, "fetch", empty_marine_fetch)
    res_ocean = client.post(
        "/api/agents/ocean/analyze",
        json={"latitude": 21.15, "longitude": 79.09, "location_name": "Inland Nagpur"},
    )
    assert res_ocean.status_code == 200
    assert res_ocean.json()["status"] == "insufficient_evidence"

    # 2. Fishing zone agent with omitted coordinates returns insufficient_evidence
    res_fish = client.post(
        "/api/agents/fishing-zone/analyze",
        json={"location_name": "Unspecified"},
    )
    assert res_fish.status_code == 200
    assert res_fish.json()["status"] == "insufficient_evidence"

    # 3. Safety/risk agent with missing wave & wind telemetry returns insufficient_evidence
    monkeypatch.setattr(safety_risk.agent.marine_provider, "fetch", empty_marine_fetch)
    async def empty_weather_fetch(*, latitude, longitude, forecast_days=1):
        return {}
    monkeypatch.setattr(safety_risk.agent.weather_provider, "fetch_weather", empty_weather_fetch)

    res_safety = client.post(
        "/api/agents/safety-risk/analyze",
        json={"latitude": 21.15, "longitude": 79.09, "vessel_type": "small_craft"},
    )
    assert res_safety.status_code == 200
    data_safety = res_safety.json()
    assert data_safety["status"] == "insufficient_evidence"
    assert data_safety["analysis"]["risk_category"] == "UNKNOWN / INSUFFICIENT EVIDENCE"
    assert not any("FAVORABLE" in r for r in data_safety["analysis"]["recommendations"])


def test_api_endpoints_provider_failure_handling(monkeypatch):
    """Verify API endpoints gracefully handle upstream provider connection/HTTP failures."""
    import httpx

    async def broken_marine_fetch(*, latitude, longitude):
        raise httpx.ConnectError("Connection refused by Open-Meteo Marine")

    monkeypatch.setattr(ocean.agent.provider, "fetch", broken_marine_fetch)
    res_ocean = client.post(
        "/api/agents/ocean/analyze",
        json={"latitude": 15.0, "longitude": 72.0},
    )
    assert res_ocean.status_code == 200
    assert res_ocean.json()["status"] == "error"
    assert "Marine provider error" in res_ocean.json()["error"]

    async def broken_weather_fetch(*, latitude, longitude, forecast_days=1):
        raise httpx.ConnectError("Connection refused by Open-Meteo Weather")

    monkeypatch.setattr(weather.agent.provider, "fetch_weather", broken_weather_fetch)
    res_weather = client.post(
        "/api/agents/weather/analyze",
        json={"latitude": 15.0, "longitude": 72.0},
    )
    assert res_weather.status_code == 200
    assert res_weather.json()["status"] == "error"
    assert "Weather provider error" in res_weather.json()["error"]

