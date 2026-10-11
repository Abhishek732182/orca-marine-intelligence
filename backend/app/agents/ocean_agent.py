"""Ocean Agent for ORCA Marine Intelligence.

An independent AI agent that analyzes wave-height conditions and sea states
using the existing Open-Meteo Marine integration, evidence validation,
and documented WMO Code Table 3700 standards without master-agent orchestration.
"""

from datetime import datetime, timezone
from typing import Any
import httpx

from app.agents.sea_state_rules import classify_sea_state
from app.data_sources.open_meteo_marine import OpenMeteoMarineProvider
from app.evidence.validator import validate_evidence
from app.schemas.agent_schemas import (
    OceanAnalyzeRequest,
    OceanAnalyzeResponse,
    OceanTimeSeriesPoint,
)


class OceanAgent:
    """Independent Ocean Agent."""

    def __init__(self, provider: OpenMeteoMarineProvider | None = None) -> None:
        self.provider = provider or OpenMeteoMarineProvider()

    async def analyze(self, request: OceanAnalyzeRequest) -> OceanAnalyzeResponse:
        """Analyze marine wave conditions and sea state."""
        lat = request.latitude
        lon = request.longitude
        loc_name = request.location_name
        window_hours = request.forecast_time_window_hours

        # 1. Coordinate range validation
        if not -90.0 <= lat <= 90.0 or not -180.0 <= lon <= 180.0:
            raise ValueError(f"Invalid coordinates: lat={lat}, lon={lon}")

        # 2. Fetch wave height records from Open-Meteo Marine
        try:
            records = await self.provider.fetch(
                latitude=lat,
                longitude=lon,
            )
        except httpx.HTTPError as exc:
            return OceanAnalyzeResponse(
                status="error",
                location={
                    "location_name": loc_name,
                    "requested_latitude": lat,
                    "requested_longitude": lon,
                },
                data_source={
                    "provider": self.provider.provider_name,
                    "endpoint": self.provider.BASE_URL,
                },
                observations={"sample_count": 0, "timeseries": []},
                analysis={"summary": f"Marine data provider connection failed: {str(exc)}"},
                warnings=["Upstream marine provider HTTP failure."],
                error=f"Marine provider error: {str(exc)}",
            )
        except ValueError as exc:
            return OceanAnalyzeResponse(
                status="error",
                location={
                    "location_name": loc_name,
                    "requested_latitude": lat,
                    "requested_longitude": lon,
                },
                data_source={"provider": self.provider.provider_name},
                observations={"sample_count": 0, "timeseries": []},
                analysis={"summary": f"Validation error: {str(exc)}"},
                warnings=[str(exc)],
                error=str(exc),
            )

        # 3. Check for empty evidence (e.g., coordinates on land)
        if not records:
            return OceanAnalyzeResponse(
                status="insufficient_evidence",
                location={
                    "location_name": loc_name,
                    "requested_latitude": lat,
                    "requested_longitude": lon,
                },
                data_source={
                    "provider": self.provider.provider_name,
                    "attribution": "Open-Meteo Marine Weather API (ECMWF / Meteo-France models)",
                },
                observations={
                    "sample_count": 0,
                    "min_wave_height_m": None,
                    "max_wave_height_m": None,
                    "avg_wave_height_m": None,
                    "latest_wave_height_m": None,
                    "timeseries": [],
                    "units": {"wave_height": "m"},
                },
                analysis={
                    "sea_state_code": None,
                    "sea_state_category": "UNKNOWN",
                    "rule_standard": "WMO Code Table 3700 / Douglas Sea Scale",
                    "summary": (
                        f"No usable wave-height records returned for '{loc_name}' "
                        f"({lat:.4f}°N, {lon:.4f}°E). Coordinates may be located on land "
                        f"or outside active numerical sea-grid coverage."
                    ),
                },
                warnings=[
                    "No marine data points returned by numerical model.",
                    "Position may be on land or beyond nautical forecast boundaries.",
                ],
            )

        # 4. Limit records to requested forecast window
        window_records = records[:window_hours] if len(records) > window_hours else records

        # 5. Validate records and collect any genuine quality issues
        all_issues: list[str] = []
        for rec in window_records:
            issues = validate_evidence(rec)
            # Guarantee future forecast timestamps are not flagged as timestamp errors
            if "forecast_data" in (rec.quality_flags or []):
                issues = [
                    i for i in issues
                    if i not in ("observation_time_in_future", "observation_after_retrieval")
                ]
            all_issues.extend(issues)

        # 6. Compute statistics
        heights = [float(r.value) for r in window_records if r.value is not None]
        if not heights:
            return OceanAnalyzeResponse(
                status="insufficient_evidence",
                location={
                    "location_name": loc_name,
                    "requested_latitude": lat,
                    "requested_longitude": lon,
                },
                data_source={"provider": self.provider.provider_name},
                observations={"sample_count": 0, "wave_height_m": None, "timeseries": []},
                analysis={
                    "sea_state_code": None,
                    "sea_state_category": "UNKNOWN",
                    "wmo_sea_state": None,
                    "summary": "All returned wave-height values were null.",
                },
                warnings=["All retrieved wave heights null."],
            )

        min_h = min(heights)
        max_h = max(heights)
        avg_h = sum(heights) / len(heights)
        latest_h = heights[0]

        # 7. Sea state classification using WMO Code Table 3700
        classification = classify_sea_state(max_h)

        timeseries_points = [
            OceanTimeSeriesPoint(
                timestamp=r.observed_at.isoformat() if r.observed_at else "",
                wave_height_m=float(r.value) if r.value is not None else None,
            )
            for r in window_records
        ]

        grid_lat = window_records[0].latitude
        grid_lon = window_records[0].longitude

        warnings = []
        if all_issues:
            warnings.append(f"Validation warnings noted: {', '.join(set(all_issues))}")
        if max_h >= 2.5:
            warnings.append(f"Rough sea advisory: Maximum wave height reaches {max_h:.2f} m.")

        summary = (
            f"Ocean wave conditions for '{loc_name}' over next {len(window_records)} hours: "
            f"Wave heights range from {min_h:.2f} m to {max_h:.2f} m (average {avg_h:.2f} m). "
            f"Sea state is classified as '{classification['category']}' (WMO Code {classification['wmo_code']})."
        )

        return OceanAnalyzeResponse(
            status="success",
            location={
                "location_name": loc_name,
                "requested_latitude": lat,
                "requested_longitude": lon,
                "grid_latitude": grid_lat,
                "grid_longitude": grid_lon,
            },
            data_source={
                "provider": self.provider.provider_name,
                "attribution": "Open-Meteo Marine Weather API (ECMWF / Meteo-France models)",
                "citation": "WMO Code Table 3700 / Douglas Sea Scale; Open-Meteo API",
            },
            observations={
                "sample_count": len(window_records),
                "wave_height_m": round(max_h, 2),
                "min_wave_height_m": round(min_h, 2),
                "max_wave_height_m": round(max_h, 2),
                "avg_wave_height_m": round(avg_h, 2),
                "latest_wave_height_m": round(latest_h, 2),
                "timeseries": timeseries_points,
                "units": {"wave_height": "m"},
            },
            analysis={
                "sea_state_code": classification["wmo_code"],
                "sea_state_category": classification["category"],
                "description": classification["description"],
                "wmo_sea_state": {
                    "code": classification["wmo_code"],
                    "category": classification["category"],
                    "description": classification["description"],
                },
                "rule_standard": classification["rule_standard"],
                "summary": summary,
            },
            warnings=warnings,
        )
