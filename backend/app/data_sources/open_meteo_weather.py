"""Open-Meteo Weather Data Provider for ORCA Weather and Safety Agents."""

from datetime import datetime, timezone
from typing import Any
import httpx


class OpenMeteoWeatherProvider:
    """Fetch real weather observations and forecasts from Open-Meteo Weather API."""

    WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
    GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

    @property
    def provider_name(self) -> str:
        return "open-meteo-weather"

    async def geocode(self, location_name: str) -> dict[str, Any] | None:
        """Resolve a textual location name to geographic coordinates."""
        if not location_name or not location_name.strip():
            return None

        params = {
            "name": location_name.strip(),
            "count": 1,
            "language": "en",
            "format": "json",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(self.GEOCODING_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        results = data.get("results")
        if isinstance(results, list) and len(results) > 0:
            first = results[0]
            return {
                "name": first.get("name", location_name),
                "latitude": float(first.get("latitude")),
                "longitude": float(first.get("longitude")),
                "country": first.get("country"),
                "admin1": first.get("admin1"),
                "elevation": first.get("elevation"),
            }
        return None

    async def fetch_weather(
        self,
        *,
        latitude: float,
        longitude: float,
        forecast_days: int = 1,
    ) -> dict[str, Any]:
        """Fetch current and hourly weather data for latitude/longitude."""
        if not -90.0 <= latitude <= 90.0:
            raise ValueError(f"Latitude must be between -90 and 90, got {latitude}")
        if not -180.0 <= longitude <= 180.0:
            raise ValueError(f"Longitude must be between -180 and 180, got {longitude}")

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current_weather": "true",
            "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,precipitation,weather_code",
            "forecast_days": max(1, min(7, forecast_days)),
            "timezone": "GMT",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(self.WEATHER_URL, params=params)
            resp.raise_for_status()
            payload = resp.json()

        return payload
