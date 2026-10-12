"""Safety/Risk Agent for ORCA Marine Intelligence.

An independent AI agent that assesses maritime hazards, sea-state risk, wind exposure,
and vessel operational limits using documented meteorological rules without master-agent orchestration.
"""

from datetime import datetime, timezone
from typing import Any
import httpx

from app.agents.sea_state_rules import classify_sea_state
from app.data_sources.open_meteo_marine import OpenMeteoMarineProvider
from app.data_sources.open_meteo_weather import OpenMeteoWeatherProvider
from app.schemas.agent_schemas import (
    SafetyRiskAnalyzeRequest,
    SafetyRiskAnalyzeResponse,
)


class SafetyRiskAgent:
    """Independent Safety/Risk Agent."""

    def __init__(
        self,
        marine_provider: OpenMeteoMarineProvider | None = None,
        weather_provider: OpenMeteoWeatherProvider | None = None,
    ) -> None:
        self.marine_provider = marine_provider or OpenMeteoMarineProvider()
        self.weather_provider = weather_provider or OpenMeteoWeatherProvider()

    async def analyze(self, request: SafetyRiskAnalyzeRequest) -> SafetyRiskAnalyzeResponse:
        """Independently assess marine hazards and operational risk."""
        lat = request.latitude
        lon = request.longitude
        loc_name = request.location_name or "Marine Position"
        vessel_type = request.vessel_type.lower()

        # Coordinate validation
        if not -90.0 <= lat <= 90.0 or not -180.0 <= lon <= 180.0:
            raise ValueError(f"Invalid coordinates: lat={lat}, lon={lon}")

        wave_h = request.wave_height_m
        wind_kts = request.wind_speed_knots
        precip_mm = request.precipitation_mm
        data_sources_used: list[str] = []
        provider_errors: list[str] = []
        warnings: list[str] = []
        is_stale = False

        # 1. Fetch live wave height if not provided
        if wave_h is None:
            try:
                marine_records = await self.marine_provider.fetch(
                    latitude=lat,
                    longitude=lon,
                )
                if marine_records:
                    wave_records = [
                        r for r in marine_records
                        if (r.variable or "").lower() in ("wave_height", "wave_height_m", "hs")
                    ]
                    if wave_records:
                        first_rec = wave_records[0]
                        now_utc = datetime.now(timezone.utc)
                        if first_rec.status == "stale":
                            is_stale = True
                            warnings.append("Marine observation record is marked 'stale'.")
                        if first_rec.retrieved_at and (now_utc - first_rec.retrieved_at).total_seconds() > 86400:
                            is_stale = True
                            warnings.append("Marine observation retrieval timestamp is stale (> 24 hours old).")

                        heights = [float(r.value) for r in wave_records if r.value is not None]
                        if heights:
                            wave_h = heights[0]
                            data_sources_used.append("Open-Meteo Marine (live)")
            except Exception as exc:
                provider_errors.append(f"Marine provider failure: {str(exc)}")

        # 2. Fetch live wind & precipitation if not provided
        if wind_kts is None or precip_mm is None:
            try:
                weather_payload = await self.weather_provider.fetch_weather(
                    latitude=lat,
                    longitude=lon,
                    forecast_days=1,
                )
                if isinstance(weather_payload, dict):
                    current = weather_payload.get("current_weather", {})
                    if wind_kts is None and "windspeed" in current:
                        kmh = current.get("windspeed")
                        if kmh is not None:
                            wind_kts = round(kmh / 1.852, 2)
                            data_sources_used.append("Open-Meteo Weather (wind)")

                    if precip_mm is None:
                        hourly = weather_payload.get("hourly", {})
                        if isinstance(hourly, dict):
                            precip_list = hourly.get("precipitation", [])
                            if precip_list:
                                precip_mm = precip_list[0] or 0.0
                                data_sources_used.append("Open-Meteo Weather (precipitation)")
            except Exception as exc:
                provider_errors.append(f"Weather provider failure: {str(exc)}")

        if request.wave_height_m is not None:
            data_sources_used.append("Manual wave observation input")
        if request.wind_speed_knots is not None:
            data_sources_used.append("Manual wind observation input")
        if request.precipitation_mm is not None:
            data_sources_used.append("Manual precipitation input")

        # 3. Handle missing data - DO NOT CLASSIFY MISSING DATA AS SAFE!
        if wave_h is None and wind_kts is None:
            err_msg = "; ".join(provider_errors) if provider_errors else None
            return SafetyRiskAnalyzeResponse(
                status="error" if provider_errors else "insufficient_evidence",
                location={"location_name": loc_name, "latitude": lat, "longitude": lon},
                data_source={
                    "providers_attempted": ["open-meteo-marine", "open-meteo-weather"],
                    "provider_errors": provider_errors,
                },
                observations={
                    "wave_height_m": None,
                    "wind_speed_knots": None,
                    "precipitation_mm": None,
                    "data_completeness": "NO_EVIDENCE_AVAILABLE",
                },
                analysis={
                    "risk_category": "UNKNOWN / INSUFFICIENT EVIDENCE",
                    "risk_score": None,
                    "risk_reasons": (
                        provider_errors if provider_errors else [
                            "No wave or wind telemetry could be retrieved for this position.",
                            "Coordinates may be on land or outside numerical model boundaries.",
                        ]
                    ),
                    "recommendations": [
                        "DO NOT PRESUME SAFE: Absence of data does NOT imply safe navigation.",
                        "Verify with local port authority and marine radio broadcasts before sailing.",
                    ],
                    "legal_notice": (
                        "ORCA Decision Support: Missing evidence cannot be assessed. "
                        "Never treat missing weather as calm or safe."
                    ),
                },
                warnings=[
                    "Missing marine observations; risk level cannot be verified.",
                    "Missing evidence is strictly NOT classified as safe.",
                ] + provider_errors,
                error=err_msg,
            )

        # 4. Evaluate specific hazard factors using explicit documented rules
        risk_reasons: list[str] = []
        factor_risks: list[str] = []
        rules_applied: list[str] = []

        # Wave height assessment
        sea_state_desc = "Unknown"
        if wave_h is not None:
            sea_classification = classify_sea_state(wave_h)
            sea_state_desc = sea_classification["category"]
            rules_applied.append(f"WMO Code Table 3700: Wave height {wave_h:.2f} m ({sea_state_desc}).")

            if vessel_type == "small_craft":
                if wave_h >= 3.0:
                    factor_risks.append("CRITICAL")
                    risk_reasons.append(f"Critical wave hazard: {wave_h:.2f} m exceeds small craft survival threshold (3.0 m).")
                elif wave_h >= 2.0:
                    factor_risks.append("HIGH")
                    risk_reasons.append(f"High wave hazard: {wave_h:.2f} m exceeds safe small craft operating envelope (2.0 m).")
                elif wave_h >= 1.25:
                    factor_risks.append("MODERATE")
                    risk_reasons.append(f"Moderate sea state: {wave_h:.2f} m causes small craft pitching and spray.")
                else:
                    factor_risks.append("LOW")
            elif vessel_type == "trawler":
                if wave_h >= 4.5:
                    factor_risks.append("CRITICAL")
                    risk_reasons.append(f"Critical sea state: {wave_h:.2f} m poses capsize risk for mechanized trawlers.")
                elif wave_h >= 3.0:
                    factor_risks.append("HIGH")
                    risk_reasons.append(f"High wave hazard: {wave_h:.2f} m requires suspension of trawling gear deployment.")
                elif wave_h >= 2.0:
                    factor_risks.append("MODERATE")
                    risk_reasons.append(f"Moderate sea state: {wave_h:.2f} m requires heavy weather precautions.")
                else:
                    factor_risks.append("LOW")
            else:  # Commercial / passenger
                if wave_h >= 6.0:
                    factor_risks.append("CRITICAL")
                    risk_reasons.append(f"Critical sea state: {wave_h:.2f} m very rough to high sea.")
                elif wave_h >= 4.0:
                    factor_risks.append("HIGH")
                    risk_reasons.append(f"High wave hazard: {wave_h:.2f} m requires speed reduction and route diversion.")
                elif wave_h >= 2.5:
                    factor_risks.append("MODERATE")
                    risk_reasons.append(f"Moderate sea: {wave_h:.2f} m passenger discomfort expected.")
                else:
                    factor_risks.append("LOW")
        else:
            risk_reasons.append("Critical safety evidence missing: Wave height data is unavailable.")
            warnings.append("Missing wave height evidence. Do not classify missing marine data as safe.")

        # Wind speed assessment
        if wind_kts is not None:
            rules_applied.append(f"Beaufort Scale: Wind speed {wind_kts:.1f} knots.")
            if wind_kts >= 34.0:
                factor_risks.append("CRITICAL")
                risk_reasons.append(f"Gale force winds: {wind_kts:.1f} knots (Beaufort 8+).")
            elif wind_kts >= 22.0:
                factor_risks.append("HIGH")
                risk_reasons.append(f"Strong breeze / Near gale: {wind_kts:.1f} knots (Beaufort 6-7).")
            elif wind_kts >= 15.0:
                factor_risks.append("MODERATE")
                risk_reasons.append(f"Moderate to fresh breeze: {wind_kts:.1f} knots.")
            else:
                factor_risks.append("LOW")
        else:
            risk_reasons.append("Critical safety evidence missing: Wind velocity is unavailable.")
            warnings.append("Missing wind velocity evidence. Do not classify missing atmospheric data as safe.")

        # Precipitation assessment
        if precip_mm is not None:
            if precip_mm >= 10.0:
                factor_risks.append("HIGH")
                risk_reasons.append(f"Torrential precipitation: {precip_mm:.1f} mm/h severe visibility reduction.")
            elif precip_mm >= 2.5:
                factor_risks.append("MODERATE")
                risk_reasons.append(f"Moderate rain: {precip_mm:.1f} mm/h reduced radar and optical visibility.")
            else:
                factor_risks.append("LOW")

        if is_stale:
            risk_reasons.append("Observation data is stale (> 24 hours old). Conditions cannot be verified.")

        # Determine composite risk level - DO NOT CLASSIFY MISSING OR STALE EVIDENCE AS SAFE/LOW!
        if "CRITICAL" in factor_risks:
            composite_risk = "CRITICAL"
            risk_score = 90
        elif "HIGH" in factor_risks:
            composite_risk = "HIGH"
            risk_score = 70
        elif wave_h is None or wind_kts is None or is_stale:
            composite_risk = "UNKNOWN / INSUFFICIENT EVIDENCE"
            risk_score = None
        elif "MODERATE" in factor_risks:
            composite_risk = "MODERATE"
            risk_score = 45
        else:
            composite_risk = "LOW"
            risk_score = 15

        # Recommendations
        recommendations = []
        if composite_risk == "CRITICAL":
            recommendations.append("DANGER: Suspend all maritime operations. Seek sheltered port immediately.")
        elif composite_risk == "HIGH":
            recommendations.append("HIGH RISK: Small craft stay ashore. Commercial vessels exercise high vigilance.")
        elif composite_risk == "UNKNOWN / INSUFFICIENT EVIDENCE":
            recommendations.append("EVIDENCE INCOMPLETE: Required marine hazard evidence is missing or stale. Do NOT assume conditions are safe or favorable.")
            recommendations.append("Obtain updated in-situ harbor reports before sailing.")
        elif composite_risk == "MODERATE":
            recommendations.append("CAUTION: Maintain watch on VHF weather channels and monitor wave developments.")
        else:
            recommendations.append("FAVORABLE: Verified wave and wind conditions are within normal baseline operating envelope for this vessel class.")

        recommendations.append("Always verify with official Coast Guard / Port Authority alerts before departing.")

        if wave_h is None or wind_kts is None:
            warnings.append("Partial evidence only: some environmental factors were unavailable.")
        if composite_risk in ("HIGH", "CRITICAL"):
            warnings.append(f"Severe maritime hazard advisory: {composite_risk} risk detected.")

        status = "insufficient_evidence" if composite_risk == "UNKNOWN / INSUFFICIENT EVIDENCE" else "success"

        return SafetyRiskAnalyzeResponse(
            status=status,
            location={"location_name": loc_name, "latitude": lat, "longitude": lon},
            data_source={
                "sources_used": data_sources_used,
                "rules_reference": "WMO Code Table 3700, Beaufort Wind Scale, IMO Vessel Seaworthiness Guidelines",
            },
            observations={
                "vessel_type": vessel_type,
                "wave_height_m": wave_h,
                "sea_state_category": sea_state_desc,
                "wind_speed_knots": wind_kts,
                "precipitation_mm": precip_mm,
                "data_completeness": "COMPLETE" if (wave_h is not None and wind_kts is not None and not is_stale) else "INCOMPLETE",
            },
            analysis={
                "risk_category": composite_risk,
                "risk_score": risk_score,
                "risk_reasons": risk_reasons,
                "rules_applied": rules_applied,
                "recommendations": recommendations,
                "legal_notice": (
                    "DECISION SUPPORT ONLY: This safety risk evaluation is an advisory support calculation. "
                    "It does NOT grant official navigation clearance, harbor master permission, or replace certified maritime watchkeeping."
                ),
            },
            warnings=warnings,
        )
