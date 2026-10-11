"""Weather Agent for ORCA Marine Intelligence.

An independent AI agent that retrieves and analyzes current and forecast weather
conditions from Open-Meteo Weather API without dependencies on any master agent.
"""

from datetime import datetime, timezone
from typing import Any
import httpx

from app.data_sources.open_meteo_weather import OpenMeteoWeatherProvider
from app.schemas.agent_schemas import (
    WeatherAnalyzeRequest,
    WeatherAnalyzeResponse,
    WeatherForecastItem,
)


def get_beaufort_scale(wind_speed_knots: float | None) -> dict[str, Any]:
    """Classify wind speed using the international Beaufort Wind Scale."""
    if wind_speed_knots is None or wind_speed_knots < 0:
        return {"force": None, "name": "Unknown", "description": "No wind observation available."}

    scales = [
        (1, 0, "Calm", "Smoke rises vertically; sea like a mirror."),
        (3, 1, "Light air", "Direction of wind shown by smoke drift, but not by wind vanes."),
        (6, 2, "Light breeze", "Wind felt on face; leaves rustle; ordinary vanes moved by wind."),
        (10, 3, "Gentle breeze", "Leaves and small twigs in constant motion; light flags extended."),
        (16, 4, "Moderate breeze", "Raises dust and loose paper; small branches are moved."),
        (21, 5, "Fresh breeze", "Small trees in leaf begin to sway; crested wavelets form on inland waters."),
        (27, 6, "Strong breeze", "Large branches in motion; whistling heard in telegraph wires; umbrellas used with difficulty."),
        (33, 7, "Near gale", "Whole trees in motion; inconvenience felt when walking against wind."),
        (40, 8, "Gale", "Breaks twigs off trees; generally impedes progress."),
        (47, 9, "Strong gale", "Slight structural damage occurs (chimney-pots and slates removed)."),
        (55, 10, "Storm", "Seldom experienced inland; trees uprooted; considerable structural damage."),
        (63, 11, "Violent storm", "Very rarely experienced; accompanied by wide-spread damage."),
        (float("inf"), 12, "Hurricane", "Devastation occurs."),
    ]

    for upper, force, name, desc in scales:
        if wind_speed_knots <= upper:
            return {"force": force, "name": name, "description": desc}

    return {"force": 12, "name": "Hurricane", "description": "Devastation occurs."}


class WeatherAgent:
    """Independent Weather Agent."""

    def __init__(self, provider: OpenMeteoWeatherProvider | None = None) -> None:
        self.provider = provider or OpenMeteoWeatherProvider()

    async def analyze(self, request: WeatherAnalyzeRequest) -> WeatherAnalyzeResponse:
        """Analyze current and forecast weather conditions."""
        lat = request.latitude
        lon = request.longitude
        loc_name = request.location_name or "Offshore Location"

        # Resolve location name if coordinates are omitted
        if lat is None or lon is None:
            if not request.location_name:
                return WeatherAnalyzeResponse(
                    status="insufficient_evidence",
                    location={
                        "location_name": "Unspecified",
                        "latitude": None,
                        "longitude": None,
                    },
                    data_source={
                        "provider": self.provider.provider_name,
                        "endpoint": self.provider.WEATHER_URL,
                    },
                    observations={},
                    forecast=[],
                    analysis={"summary": "Neither geographic coordinates nor location name were provided."},
                    warnings=["Input missing latitude/longitude and location name."],
                    error="Coordinates or location name required.",
                )

            # Geocode
            try:
                geo = await self.provider.geocode(request.location_name)
            except httpx.HTTPError as exc:
                return WeatherAnalyzeResponse(
                    status="error",
                    location={"location_name": request.location_name, "latitude": None, "longitude": None},
                    data_source={"provider": self.provider.provider_name},
                    observations={},
                    forecast=[],
                    analysis={"summary": f"Geocoding service unavailable: {str(exc)}"},
                    warnings=["Failed to contact geocoding service."],
                    error=str(exc),
                )

            if not geo:
                return WeatherAnalyzeResponse(
                    status="insufficient_evidence",
                    location={"location_name": request.location_name, "latitude": None, "longitude": None},
                    data_source={"provider": self.provider.provider_name},
                    observations={},
                    forecast=[],
                    analysis={"summary": f"Could not geocode location name '{request.location_name}' into coordinates."},
                    warnings=[f"Geocoding yielded no match for '{request.location_name}'."],
                    error="Location geocoding failed.",
                )

            lat = geo["latitude"]
            lon = geo["longitude"]
            loc_name = f"{geo['name']}, {geo.get('country', '')}".strip(", ")

        # Validate coordinates range
        if not -90.0 <= lat <= 90.0 or not -180.0 <= lon <= 180.0:
            raise ValueError(f"Invalid coordinates: lat={lat}, lon={lon}")

        # Fetch live weather data
        try:
            payload = await self.provider.fetch_weather(
                latitude=lat,
                longitude=lon,
                forecast_days=request.forecast_days,
            )
        except httpx.HTTPError as exc:
            return WeatherAnalyzeResponse(
                status="error",
                location={"location_name": loc_name, "latitude": lat, "longitude": lon},
                data_source={"provider": self.provider.provider_name, "endpoint": self.provider.WEATHER_URL},
                observations={},
                forecast=[],
                analysis={"summary": f"Weather data provider connection failed: {str(exc)}"},
                warnings=["Upstream provider HTTP error."],
                error=f"Weather provider error: {str(exc)}",
            )
        except ValueError as exc:
            return WeatherAnalyzeResponse(
                status="error",
                location={"location_name": loc_name, "latitude": lat, "longitude": lon},
                data_source={"provider": self.provider.provider_name},
                observations={},
                forecast=[],
                analysis={"summary": f"Validation error: {str(exc)}"},
                warnings=[str(exc)],
                error=str(exc),
            )

        current = payload.get("current_weather", {})
        hourly = payload.get("hourly", {})

        if not current and not hourly:
            return WeatherAnalyzeResponse(
                status="insufficient_evidence",
                location={"location_name": loc_name, "latitude": lat, "longitude": lon},
                data_source={"provider": self.provider.provider_name},
                observations={},
                forecast=[],
                analysis={"summary": "Provider returned empty weather data for requested coordinates."},
                warnings=["Empty weather payload from provider."],
            )

        # Parse current observations
        wind_speed_kmh = current.get("windspeed")
        wind_speed_knots = round(wind_speed_kmh / 1.852, 2) if wind_speed_kmh is not None else None
        temp_c = current.get("temperature")
        wind_dir = current.get("winddirection")
        weather_code = current.get("weathercode")
        obs_time = current.get("time")

        beaufort = get_beaufort_scale(wind_speed_knots)

        # Build hourly forecast
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        speeds = hourly.get("wind_speed_10m", [])
        dirs = hourly.get("wind_direction_10m", [])
        precips = hourly.get("precipitation", [])

        forecast_items: list[WeatherForecastItem] = []
        max_items = min(len(times), request.forecast_days * 24)
        total_precip = 0.0

        for i in range(max_items):
            t_kmh = speeds[i] if i < len(speeds) else None
            t_kts = round(t_kmh / 1.852, 2) if t_kmh is not None else None
            p_val = precips[i] if i < len(precips) else 0.0
            if p_val:
                total_precip += p_val

            forecast_items.append(
                WeatherForecastItem(
                    timestamp=times[i] if i < len(times) else "",
                    temperature_c=temps[i] if i < len(temps) else None,
                    wind_speed_kmh=t_kmh,
                    wind_speed_knots=t_kts,
                    wind_direction_deg=dirs[i] if i < len(dirs) else None,
                    precipitation_mm=p_val,
                )
            )

        warnings: list[str] = []
        if wind_speed_knots and wind_speed_knots >= 22.0:
            warnings.append(f"High wind warning: {wind_speed_knots} knots ({beaufort['name']}).")
        if total_precip > 15.0:
            warnings.append(f"Significant precipitation expected: {round(total_precip, 1)} mm.")

        summary = (
            f"Current weather at {loc_name} ({lat:.4f}°N, {lon:.4f}°E): "
            f"Temperature is {temp_c}°C, wind is {wind_speed_knots} knots from {wind_dir}° "
            f"({beaufort['name']}, Beaufort Force {beaufort['force']}). "
            f"Forecast coverage spans {len(forecast_items)} hours with {round(total_precip, 1)} mm cumulative precipitation."
        )

        return WeatherAnalyzeResponse(
            status="success",
            location={
                "location_name": loc_name,
                "latitude": float(payload.get("latitude", lat)),
                "longitude": float(payload.get("longitude", lon)),
                "elevation": payload.get("elevation"),
                "timezone": payload.get("timezone", "GMT"),
            },
            data_source={
                "provider": self.provider.provider_name,
                "attribution": "Open-Meteo Weather API",
                "endpoint": self.provider.WEATHER_URL,
            },
            observations={
                "timestamp": obs_time,
                "temperature_c": temp_c,
                "wind_speed_kmh": wind_speed_kmh,
                "wind_speed_knots": wind_speed_knots,
                "wind_direction_deg": wind_dir,
                "weather_code": weather_code,
                "beaufort_scale": beaufort,
            },
            forecast=forecast_items,
            analysis={
                "summary": summary,
                "beaufort_scale": beaufort,
                "total_forecast_precipitation_mm": round(total_precip, 2),
                "forecast_hours": len(forecast_items),
            },
            warnings=warnings,
        )
