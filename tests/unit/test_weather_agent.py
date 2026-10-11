"""Unit tests for independent Weather Agent."""

import pytest
import httpx
from unittest.mock import AsyncMock

from app.agents.weather_agent import WeatherAgent, get_beaufort_scale
from app.schemas.agent_schemas import WeatherAnalyzeRequest


@pytest.fixture
def mock_weather_provider():
    provider = AsyncMock()
    provider.provider_name = "open-meteo-weather"
    provider.WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
    provider.GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
    return provider


def test_beaufort_scale_classifications():
    assert get_beaufort_scale(0)["force"] == 0
    assert get_beaufort_scale(2)["force"] == 1
    assert get_beaufort_scale(5)["force"] == 2
    assert get_beaufort_scale(15)["force"] == 4
    assert get_beaufort_scale(25)["force"] == 6
    assert get_beaufort_scale(35)["force"] == 8
    assert get_beaufort_scale(65)["force"] == 12
    assert get_beaufort_scale(None)["force"] is None
    assert get_beaufort_scale(-5)["force"] is None


@pytest.mark.asyncio
async def test_weather_agent_valid_coordinates(mock_weather_provider):
    mock_weather_provider.fetch_weather.return_value = {
        "latitude": 15.0,
        "longitude": 72.0,
        "elevation": 0.0,
        "timezone": "GMT",
        "current_weather": {
            "time": "2026-10-11T12:00",
            "temperature": 28.5,
            "windspeed": 22.0,  # km/h
            "winddirection": 240.0,
            "weathercode": 2,
        },
        "hourly": {
            "time": ["2026-10-11T12:00", "2026-10-11T13:00"],
            "temperature_2m": [28.5, 28.2],
            "wind_speed_10m": [22.0, 20.0],
            "wind_direction_10m": [240.0, 245.0],
            "precipitation": [0.0, 0.5],
        },
    }

    agent = WeatherAgent(provider=mock_weather_provider)
    request = WeatherAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        location_name="Offshore Goa",
        forecast_days=1,
    )
    response = await agent.analyze(request)

    assert response.agent == "Weather Agent"
    assert response.status == "success"
    assert response.location["latitude"] == 15.0
    assert response.location["longitude"] == 72.0
    assert response.observations["temperature_c"] == 28.5
    assert response.observations["wind_speed_kmh"] == 22.0
    assert response.observations["wind_speed_knots"] == 11.88
    assert len(response.forecast) == 2
    assert response.analysis["beaufort_scale"]["force"] == 4
    assert response.error is None


@pytest.mark.asyncio
async def test_weather_agent_geocoding_lookup(mock_weather_provider):
    mock_weather_provider.geocode.return_value = {
        "name": "Panaji",
        "latitude": 15.4989,
        "longitude": 73.8278,
        "country": "India",
    }
    mock_weather_provider.fetch_weather.return_value = {
        "latitude": 15.5,
        "longitude": 73.8,
        "current_weather": {"temperature": 30.0, "windspeed": 10.0, "winddirection": 180.0},
        "hourly": {"time": ["2026-10-11T12:00"], "temperature_2m": [30.0], "wind_speed_10m": [10.0]},
    }

    agent = WeatherAgent(provider=mock_weather_provider)
    request = WeatherAnalyzeRequest(location_name="Panaji")
    response = await agent.analyze(request)

    assert response.status == "success"
    assert response.location["latitude"] == 15.5
    assert mock_weather_provider.geocode.called


@pytest.mark.asyncio
async def test_weather_agent_missing_input(mock_weather_provider):
    agent = WeatherAgent(provider=mock_weather_provider)
    request = WeatherAnalyzeRequest()
    response = await agent.analyze(request)

    assert response.status == "insufficient_evidence"
    assert isinstance(response.error, str), f"Expected string error, got: {response.error!r}"
    assert "Coordinates or location name required" in response.error


@pytest.mark.asyncio
async def test_weather_agent_invalid_coordinates(mock_weather_provider):
    agent = WeatherAgent(provider=mock_weather_provider)
    with pytest.raises(Exception):
        request = WeatherAnalyzeRequest(latitude=95.0, longitude=72.0)
        await agent.analyze(request)


@pytest.mark.asyncio
async def test_weather_agent_provider_failure(mock_weather_provider):
    mock_weather_provider.fetch_weather.side_effect = httpx.ConnectError("Network connection lost")

    agent = WeatherAgent(provider=mock_weather_provider)
    request = WeatherAnalyzeRequest(latitude=15.0, longitude=72.0)
    response = await agent.analyze(request)

    assert response.status == "error"
    assert isinstance(response.error, str), f"Expected string error, got: {response.error!r}"
    assert "Network connection lost" in response.error
    assert "Upstream provider HTTP error" in response.warnings[0]


@pytest.mark.asyncio
async def test_weather_agent_empty_evidence(mock_weather_provider):
    mock_weather_provider.fetch_weather.return_value = {
        "current_weather": {},
        "hourly": {},
    }

    agent = WeatherAgent(provider=mock_weather_provider)
    request = WeatherAnalyzeRequest(latitude=15.0, longitude=72.0)
    response = await agent.analyze(request)

    assert response.status == "insufficient_evidence"
    assert "Empty weather payload" in response.warnings[0]
