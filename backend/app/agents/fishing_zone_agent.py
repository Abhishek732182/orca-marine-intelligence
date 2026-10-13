"""Fishing Zone Agent for ORCA Marine Intelligence (Agent 3).

An independent AI specialist agent that evaluates marine operational sea conditions
and fisheries indicators using evidence-grounded rules.

Architectural and Evidence Guarantees:
1. Strict Evidence Separation: Clearly distinguishes measured provider observations,
   environmental habitat bounds, operational sea-state feasibility, and biological fish telemetry.
2. No Data Fabrication: Never invents fish locations, biomass, species distributions,
   catch probabilities, or fishing coordinates when biological telemetry is unavailable.
3. Explicit Uncertainty: If fisheries or fish-distribution data is missing or stale, returns
   status 'insufficient_evidence' and zone suitability 'INSUFFICIENT_EVIDENCE' or 'UNKNOWN'.
4. Operational Safety Separation: Physical wave height and weather evaluate vessel craft
   operability only; they do NOT prove fish are present or grant maritime sailing clearance.
5. Transparent Scoring: Documents all inputs, units, thresholds, weights, and limitations.
   Never silently substitutes zeros or arbitrary defaults for missing variables.
   Returns no numeric score when biological evidence is insufficient or stale.
6. Provenance Preservation: Preserves source provider names, timestamps, units, coordinates,
   evidence IDs, and data coverage for every valid observed variable.
7. Freshness Enforcement: Strictly rejects stale or invalid evidence records according
   to documented marine freshness rules.
8. Deterministic Evaluation: Repeated queries for identical time windows and source data
   produce consistent, reproducible evaluations.
"""

from datetime import datetime, timedelta, timezone
import logging
import math
from typing import Any
import httpx

from app.agents.biological_prediction_agent import (
    BiologicalFeatureVector,
    BiologicalModelInterface,
    EnvironmentalEvidence,
    analyze_environment,
)
from app.agents.sea_state_rules import classify_sea_state
from app.agents.species_rules import (
    evaluate_thermal_suitability,
    lookup_species,
)
from app.data_sources.base import MarineDataProvider
from app.data_sources.open_meteo_marine import OpenMeteoMarineProvider
from app.evidence.freshness import is_stale
from app.evidence.validator import validate_evidence
from app.schemas.agent_schemas import (
    FishingZoneAnalyzeRequest,
    FishingZoneAnalyzeResponse,
)
from app.schemas.evidence import EvidenceRecord

logger = logging.getLogger("orca.agents.fishing_zone")

# Connected and Missing Provider Registry
CONNECTED_PROVIDERS = ["open-meteo-marine"]
MISSING_FISHERIES_PROVIDERS = [
    "INCOIS Potential Fishing Zone (PFZ) advisory service",
    "Copernicus Marine Environment Monitoring Service (CMEMS)",
    "NOAA CoastWatch Ocean Color / Chlorophyll-a telemetry",
    "In-situ acoustic fish survey / commercial fisheries landings logs",
]
RECOMMENDED_INTEGRATIONS = [
    "INCOIS PFZ REST API / Web Feature Service (WFS) for Indian Exclusive Economic Zone (EEZ)",
    "Copernicus Marine CMEMS Global Biogeochemical Analysis (Sentinel-3 OLCI Chlorophyll-a)",
    "NOAA ERDDAP CoastWatch SST and Ocean Color satellite products",
    "National Marine Fisheries Service (NMFS) acoustic pelagic trawl survey telemetry",
]

STANDARD_LIMITATIONS = [
    "Open-Meteo Marine API supplies physical wave forecasts (Hs, wave period, direction) only.",
    "Satellite ocean color (chlorophyll-a) and sea surface temperature (SST) require multispectral infrared sensors (e.g. MODIS, VIIRS, Sentinel-3).",
    "Direct pelagic fish biomass requires acoustic sonar surveys, echosounders, or fishery catch logs.",
    "ORCA strictly evaluates verifiable observations and never fabricates coordinates or biomass densities.",
]


class FishingZoneAgent:
    """Independent Fishing Zone Specialist Agent."""

    def __init__(
        self,
        provider: MarineDataProvider | OpenMeteoMarineProvider | None = None,
        fisheries_provider: Any | None = None,
        biological_model: BiologicalModelInterface | None = None,
    ) -> None:
        self.provider = provider or OpenMeteoMarineProvider()
        self.fisheries_provider = fisheries_provider
        self.biological_model = biological_model

    def _evaluate_biological_evidence(
        self,
        wave_rec: EvidenceRecord | None = None,
        sst_rec: EvidenceRecord | None = None,
        chla_rec: EvidenceRecord | None = None,
        now: datetime | None = None,
        target_species: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> dict[str, Any]:
        """Evaluate evidence completeness using biological prediction module without fabricating presence."""
        now_dt = now or datetime.now(timezone.utc)
        wave_val: float | None = None
        if wave_rec and wave_rec.value is not None:
            try:
                v = float(wave_rec.value)
                if 0 <= v <= 50:
                    wave_val = v
            except (ValueError, TypeError):
                wave_val = None

        sst_val: float | None = None
        if sst_rec and sst_rec.value is not None:
            try:
                v = float(sst_rec.value)
                if -5 <= v <= 50:
                    sst_val = v
            except (ValueError, TypeError):
                sst_val = None

        chla_val: float | None = None
        if chla_rec and chla_rec.value is not None:
            try:
                v = float(chla_rec.value)
                if 0 <= v <= 100:
                    chla_val = v
            except (ValueError, TypeError):
                chla_val = None

        try:
            env_evidence = EnvironmentalEvidence(
                wave_height_m=wave_val,
                wave_observed_at=wave_rec.observed_at if wave_rec and wave_val is not None else None,
                wave_source=wave_rec.source if wave_rec and wave_val is not None else None,
                sea_surface_temperature_c=sst_val,
                sst_observed_at=sst_rec.observed_at if sst_rec and sst_val is not None else None,
                sst_source=sst_rec.source if sst_rec and sst_val is not None else None,
                chlorophyll_a_mg_m3=chla_val,
                chlorophyll_observed_at=chla_rec.observed_at if chla_rec and chla_val is not None else None,
                chlorophyll_source=chla_rec.source if chla_rec and chla_val is not None else None,
            )
        except Exception:
            env_evidence = EnvironmentalEvidence()

        feature_vec: BiologicalFeatureVector | None = None
        if self.biological_model is not None and target_species and latitude is not None and longitude is not None:
            try:
                feature_vec = BiologicalFeatureVector(
                    species_code=target_species,
                    latitude=latitude,
                    longitude=longitude,
                    observed_at=sst_rec.observed_at if sst_rec and sst_rec.observed_at else now_dt,
                    sea_surface_temperature_c=sst_val,
                    chlorophyll_a_mg_m3=chla_val,
                )
            except Exception:
                feature_vec = None

        return analyze_environment(
            env_evidence,
            model=self.biological_model,
            feature_vector=feature_vec,
            now=now_dt,
        )

    async def analyze(self, request: FishingZoneAnalyzeRequest) -> FishingZoneAnalyzeResponse:
        """Analyze marine conditions, vessel feasibility, and fisheries suitability."""
        lat = request.latitude
        lon = request.longitude
        window_hours = request.forecast_time_window_hours or 24
        target_species_raw = request.target_species

        # ----------------------------------------------------------------------
        # 1. Coordinate Validation & Geographic Sector Characterization
        # ----------------------------------------------------------------------
        if lat is None or lon is None:
            return FishingZoneAnalyzeResponse(
                status="insufficient_evidence",
                location=None,
                data_source={
                    "provider": getattr(self.provider, "provider_name", "open-meteo-marine"),
                    "coverage": "Global marine numerical grid",
                    "connected_providers": CONNECTED_PROVIDERS,
                    "contributing_sources": [],
                    "missing_providers": MISSING_FISHERIES_PROVIDERS,
                    "recommended_integrations": RECOMMENDED_INTEGRATIONS,
                    "rejected_records_count": 0,
                    "rejected_records": [],
                    "rejected_records_reasons": [],
                },
                observations={},
                analysis={
                    "zone_suitability": "UNKNOWN",
                    "operational_feasibility": "UNVERIFIED",
                    "operational_feasibility_scope": "STRICTLY_PHYSICAL_WAVE_CONDITIONS",
                    "criteria_applied": [
                        "Geographic coordinates are required to query marine conditions."
                    ],
                    "fish_distribution_disclaimer": (
                        "No coordinates provided. Direct fish location telemetry is not accessible."
                    ),
                    "scoring": {
                        "suitability_score": None,
                        "confidence_level": "INSUFFICIENT_EVIDENCE",
                        "evidence_coverage_pct": 0.0,
                        "rationale": "Missing coordinates prevent querying environmental or fisheries telemetry.",
                    },
                    "biological_prediction": self._evaluate_biological_evidence(),
                },
                warnings=["Missing latitude and longitude coordinates."],
                error="Coordinates required for marine fisheries analysis.",
            )

        if not -90.0 <= lat <= 90.0 or not -180.0 <= lon <= 180.0:
            raise ValueError(f"Invalid coordinates: lat={lat}, lon={lon}")

        # Geographic nomenclature disambiguation for coordinates 15.0°N, 72.0°E
        # (15.0°N, 72.0°E is approx 185 km west of the Goa coastline, in deep offshore waters > 1500m depth)
        is_goa_offshore = abs(lat - 15.0) <= 0.5 and abs(lon - 72.0) <= 0.5
        if not request.location_name:
            loc_name = "Goa Offshore Waters" if is_goa_offshore else f"Offshore Sector ({lat:.4f}°N, {lon:.4f}°E)"
        else:
            loc_name = request.location_name

        location_payload: dict[str, Any] = {
            "location_name": loc_name,
            "latitude": lat,
            "longitude": lon,
        }

        if is_goa_offshore:
            location_payload["geographic_characterization"] = {
                "sector_classification": "Offshore Oceanic Waters (Deep Arabian Sea)",
                "distance_to_nearest_coastline_km": 185.0,
                "distance_to_nearest_coastline_nm": 99.9,
                "bathymetric_zone": "Continental Slope / Oceanic Pelagic (> 1500 m depth)",
                "nomenclature_distinction": (
                    "Coordinates 15.0°N, 72.0°E designated as 'Goa Offshore Waters' lie in the open Arabian Sea deep basin (~185 km west of Goa). "
                    "Distinct from nearshore 'Goa Coastal Sector' (< 12 nm artisanal waters)."
                ),
            }

        # Target species verification using documented registry
        species_lookup = lookup_species(target_species_raw)
        species_status = species_lookup.get("status")
        species_name_queried = target_species_raw or "General Pelagic/Demersal"

        # ----------------------------------------------------------------------
        # 2. Fetch Evidence from Connected Marine Provider & Fisheries Sources
        # ----------------------------------------------------------------------
        try:
            raw_records = await self.provider.fetch(
                latitude=lat,
                longitude=lon,
            )
            # Query resilient fisheries/satellite provider if injected
            if self.fisheries_provider is not None:
                try:
                    fish_records = await self.fisheries_provider.fetch(
                        latitude=lat,
                        longitude=lon,
                    )
                    if fish_records:
                        raw_records = list(raw_records or []) + list(fish_records)
                except Exception as fish_exc:
                    logger.debug("Fisheries provider query skipped or failed: %s", fish_exc)
        except httpx.HTTPError as exc:
            return FishingZoneAnalyzeResponse(
                status="error",
                location=location_payload,
                data_source={
                    "provider": getattr(self.provider, "provider_name", "open-meteo-marine"),
                    "connected_providers": CONNECTED_PROVIDERS,
                    "contributing_sources": [],
                    "rejected_records_count": 0,
                    "rejected_records": [],
                    "rejected_records_reasons": [],
                },
                observations={},
                analysis={
                    "summary": f"Marine data provider connection failed: {str(exc)}",
                    "biological_prediction": self._evaluate_biological_evidence(),
                },
                warnings=["Upstream marine provider error."],
                error=f"Marine provider error: {str(exc)}",
            )
        except ValueError as exc:
            return FishingZoneAnalyzeResponse(
                status="error",
                location=location_payload,
                data_source={
                    "provider": getattr(self.provider, "provider_name", "open-meteo-marine"),
                    "connected_providers": CONNECTED_PROVIDERS,
                    "contributing_sources": [],
                    "rejected_records_count": 0,
                    "rejected_records": [],
                    "rejected_records_reasons": [],
                },
                observations={},
                analysis={
                    "summary": f"Validation error: {str(exc)}",
                    "biological_prediction": self._evaluate_biological_evidence(),
                },
                warnings=[str(exc)],
                error=str(exc),
            )
        except Exception as exc:
            return FishingZoneAnalyzeResponse(
                status="error",
                location=location_payload,
                data_source={
                    "provider": getattr(self.provider, "provider_name", "open-meteo-marine"),
                    "connected_providers": CONNECTED_PROVIDERS,
                    "contributing_sources": [],
                    "rejected_records_count": 0,
                    "rejected_records": [],
                    "rejected_records_reasons": [],
                },
                observations={},
                analysis={
                    "summary": f"Provider extraction failed: {str(exc)}",
                    "biological_prediction": self._evaluate_biological_evidence(),
                },
                warnings=[f"Provider error: {str(exc)}"],
                error=f"Unexpected provider error: {str(exc)}",
            )

        # ----------------------------------------------------------------------
        # 3. Handle Empty Evidence (Land or Model Void)
        # ----------------------------------------------------------------------
        if not raw_records:
            return FishingZoneAnalyzeResponse(
                status="insufficient_evidence",
                location=location_payload,
                data_source={
                    "provider": getattr(self.provider, "provider_name", "open-meteo-marine"),
                    "attribution": "Open-Meteo Marine Weather API",
                    "connected_providers": CONNECTED_PROVIDERS,
                    "contributing_sources": [],
                    "missing_providers": MISSING_FISHERIES_PROVIDERS,
                    "recommended_integrations": RECOMMENDED_INTEGRATIONS,
                    "rejected_records_count": 0,
                    "rejected_records": [],
                    "rejected_records_reasons": [],
                },
                observations={"wave_records_count": 0},
                analysis={
                    "zone_suitability": "INSUFFICIENT_EVIDENCE",
                    "operational_feasibility": "NON_NAVIGABLE_OR_INLAND",
                    "operational_feasibility_scope": "STRICTLY_PHYSICAL_WAVE_CONDITIONS",
                    "target_species_queried": species_name_queried,
                    "criteria_applied": [
                        "Coordinates returned no marine numerical grid cells.",
                        "Position may be on land or beyond model sea coverage.",
                    ],
                    "fish_distribution_disclaimer": (
                        "No oceanographic or fisheries data available for this position. "
                        "Fish distributions cannot be determined."
                    ),
                    "scoring": {
                        "suitability_score": None,
                        "confidence_level": "INSUFFICIENT_EVIDENCE",
                        "evidence_coverage_pct": 0.0,
                        "rationale": "No marine numerical grid cells found at coordinates; inland or unnavigable.",
                    },
                    "biological_prediction": self._evaluate_biological_evidence(),
                },
                warnings=[
                    "No marine data points returned by provider.",
                    "Position appears inland or outside oceanographic grid.",
                ],
                error="No marine numerical grid data returned. Position may be inland or outside oceanographic model coverage.",
            )

        # ----------------------------------------------------------------------
        # 4. Deterministic Sorting, Strict Validation, Freshness & Rejection
        # ----------------------------------------------------------------------
        records = sorted(
            raw_records,
            key=lambda r: (
                r.variable or "",
                r.observed_at or datetime.min.replace(tzinfo=timezone.utc),
                r.evidence_id or "",
            ),
        )

        now_utc = datetime.now(timezone.utc)
        validation_warnings: list[str] = []
        rejected_records: list[dict[str, Any]] = []
        contributing_sources: set[str] = set()

        fresh_valid_wave: list[EvidenceRecord] = []
        fresh_valid_sst: list[EvidenceRecord] = []
        fresh_valid_chla: list[EvidenceRecord] = []
        fresh_valid_bio: list[EvidenceRecord] = []

        all_wave_records: list[EvidenceRecord] = []
        all_sst_records: list[EvidenceRecord] = []
        all_chla_records: list[EvidenceRecord] = []
        all_bio_records: list[EvidenceRecord] = []

        for rec in records:
            var_cand = (rec.variable or "").lower()
            if var_cand in ["wave_height", "wave_height_m", "hs"]:
                all_wave_records.append(rec)
            elif var_cand in ["sea_surface_temperature", "sst", "temperature_c"]:
                all_sst_records.append(rec)
            elif var_cand in ["chlorophyll_a", "chla", "chlor_a"]:
                all_chla_records.append(rec)
            elif var_cand in ["fish_biomass", "biomass", "potential_fishing_zone"]:
                all_bio_records.append(rec)

            issues = validate_evidence(rec, now=now_utc)
            is_forecast = "forecast_data" in (rec.quality_flags or [])
            stale = is_stale(rec, now=now_utc, allow_forecast=is_forecast)

            # Check status
            if rec.status != "valid":
                reason = f"Record status is '{rec.status}', not 'valid'"
                logger.info(
                    "FishingZoneAgent: Rejected record %s (%s, source=%s): %s",
                    rec.evidence_id,
                    rec.variable,
                    rec.source,
                    reason,
                )
                rejected_records.append({
                    "evidence_id": rec.evidence_id,
                    "variable": rec.variable,
                    "source": rec.source,
                    "observed_at": rec.observed_at.isoformat() if rec.observed_at else None,
                    "reason": reason,
                })
                continue

            # Check validation issues (allowing future observation for forecast_data)
            fatal_issues = [
                i for i in issues
                if not (is_forecast and i in ("observation_time_in_future", "observation_after_retrieval"))
            ]
            if fatal_issues:
                reason = f"Validation issues: {', '.join(fatal_issues)}"
                logger.info(
                    "FishingZoneAgent: Rejected record %s (%s, source=%s): %s",
                    rec.evidence_id,
                    rec.variable,
                    rec.source,
                    reason,
                )
                validation_warnings.append(
                    f"Record {rec.evidence_id} ({rec.variable}) rejected due to validation issues: {', '.join(fatal_issues)}."
                )
                rejected_records.append({
                    "evidence_id": rec.evidence_id,
                    "variable": rec.variable,
                    "source": rec.source,
                    "observed_at": rec.observed_at.isoformat() if rec.observed_at else None,
                    "reason": reason,
                })
                continue

            # Freshness rule check
            if stale:
                time_str = rec.observed_at.isoformat() if rec.observed_at else "null"
                reason = "Observation timestamp is stale under documented freshness rules."
                logger.info(
                    "FishingZoneAgent: Rejected stale record %s (%s, observed_at=%s)",
                    rec.evidence_id,
                    rec.variable,
                    time_str,
                )
                rejected_records.append({
                    "evidence_id": rec.evidence_id,
                    "variable": rec.variable,
                    "source": rec.source,
                    "observed_at": time_str,
                    "reason": reason,
                })
                continue

            # Value check
            try:
                val = float(rec.value) if rec.value is not None else None
            except (ValueError, TypeError):
                val = None

            if val is None or math.isnan(val):
                reason = "Observation value is null or non-numeric."
                logger.info(
                    "FishingZoneAgent: Rejected record %s (%s, source=%s): %s",
                    rec.evidence_id,
                    rec.variable,
                    rec.source,
                    reason,
                )
                rejected_records.append({
                    "evidence_id": rec.evidence_id,
                    "variable": rec.variable,
                    "source": rec.source,
                    "observed_at": rec.observed_at.isoformat() if rec.observed_at else None,
                    "reason": reason,
                })
                continue

            var = (rec.variable or "").lower()

            # Physical plausibility checks
            if var in ["wave_height", "wave_height_m", "hs"]:
                if val < 0.0 or val > 30.0:
                    reason = f"Wave height ({val} m) is physically invalid."
                    logger.info(
                        "FishingZoneAgent: Rejected physically invalid wave %s: %s",
                        rec.evidence_id,
                        reason,
                    )
                    rejected_records.append({
                        "evidence_id": rec.evidence_id,
                        "variable": rec.variable,
                        "source": rec.source,
                        "observed_at": rec.observed_at.isoformat() if rec.observed_at else None,
                        "reason": reason,
                    })
                    continue
                fresh_valid_wave.append(rec)
                if rec.source:
                    contributing_sources.add(rec.source)

            elif var in ["sea_surface_temperature", "sst", "temperature_c"]:
                if val < -2.0 or val > 45.0:
                    reason = f"SST ({val} °C) is physically invalid."
                    logger.info(
                        "FishingZoneAgent: Rejected physically invalid SST %s: %s",
                        rec.evidence_id,
                        reason,
                    )
                    rejected_records.append({
                        "evidence_id": rec.evidence_id,
                        "variable": rec.variable,
                        "source": rec.source,
                        "observed_at": rec.observed_at.isoformat() if rec.observed_at else None,
                        "reason": reason,
                    })
                    continue
                fresh_valid_sst.append(rec)
                if rec.source:
                    contributing_sources.add(rec.source)

            elif var in ["chlorophyll_a", "chlorophyll", "chla"]:
                if val < 0.0 or val > 100.0:
                    reason = f"Chlorophyll-a ({val} mg/m³) is physically invalid."
                    logger.info(
                        "FishingZoneAgent: Rejected physically invalid chla %s: %s",
                        rec.evidence_id,
                        reason,
                    )
                    rejected_records.append({
                        "evidence_id": rec.evidence_id,
                        "variable": rec.variable,
                        "source": rec.source,
                        "observed_at": rec.observed_at.isoformat() if rec.observed_at else None,
                        "reason": reason,
                    })
                    continue
                fresh_valid_chla.append(rec)
                if rec.source:
                    contributing_sources.add(rec.source)

            elif var in ["fish_biomass", "fish_density", "catch_density", "pelagic_abundance", "biomass"]:
                if val < 0.0:
                    reason = f"Fish biomass ({val} kg/km²) is physically invalid."
                    logger.info(
                        "FishingZoneAgent: Rejected physically invalid biomass %s: %s",
                        rec.evidence_id,
                        reason,
                    )
                    rejected_records.append({
                        "evidence_id": rec.evidence_id,
                        "variable": rec.variable,
                        "source": rec.source,
                        "observed_at": rec.observed_at.isoformat() if rec.observed_at else None,
                        "reason": reason,
                    })
                    continue
                fresh_valid_bio.append(rec)
                if rec.source:
                    contributing_sources.add(rec.source)

        # ----------------------------------------------------------------------
        # 5. Physical Wave Height & Sea State Processing
        # ----------------------------------------------------------------------
        # Filter wave records within the requested forecast window horizon
        window_horizon = now_utc + timedelta(hours=window_hours)
        window_wave = [
            r for r in fresh_valid_wave
            if r.observed_at is None or r.observed_at <= window_horizon
        ]
        if not window_wave and fresh_valid_wave:
            window_wave = fresh_valid_wave[:window_hours]

        valid_heights = [float(r.value) for r in window_wave if r.value is not None]

        if not valid_heights:
            return FishingZoneAnalyzeResponse(
                status="insufficient_evidence",
                location=location_payload,
                data_source={
                    "provider": getattr(self.provider, "provider_name", "open-meteo-marine"),
                    "connected_providers": CONNECTED_PROVIDERS,
                    "contributing_sources": list(contributing_sources),
                    "rejected_records_count": len(rejected_records),
                    "rejected_records": rejected_records,
                    "rejected_records_reasons": sorted(list({r["reason"] for r in rejected_records})),
                },
                observations={"wave_records_count": 0, "accepted_records_count": 0, "rejected_records_count": len(rejected_records)},
                analysis={
                    "zone_suitability": "INSUFFICIENT_EVIDENCE",
                    "operational_feasibility": "UNVERIFIED",
                    "operational_feasibility_scope": "STRICTLY_PHYSICAL_WAVE_CONDITIONS",
                    "criteria_applied": [
                        "All wave height measurements were null, invalid, or rejected as stale."
                    ],
                    "scoring": {
                        "suitability_score": None,
                        "confidence_level": "INSUFFICIENT_EVIDENCE",
                        "evidence_coverage_pct": 0.0,
                        "rationale": "Missing valid fresh wave measurements.",
                    },
                    "biological_prediction": self._evaluate_biological_evidence(
                        wave_rec=all_wave_records[-1] if all_wave_records else None,
                        sst_rec=all_sst_records[-1] if all_sst_records else None,
                        chla_rec=all_chla_records[-1] if all_chla_records else None,
                        now=now_utc,
                    ),
                },
                warnings=["Null wave height records."],
                error="Null wave height records returned by provider.",
            )

        # Wave height metrics calculated ONLY from accepted, valid observations
        max_wave_m = max(valid_heights)
        avg_wave_m = sum(valid_heights) / len(valid_heights)
        latest_wave_rec = window_wave[-1]
        sea_state = classify_sea_state(max_wave_m)

        # Hours evaluated and temporal coverage calculated from actual observation timestamps
        wave_timestamps = [r.observed_at for r in window_wave if r.observed_at is not None]
        if len(wave_timestamps) >= 2:
            earliest_obs_time = min(wave_timestamps)
            latest_obs_time = max(wave_timestamps)
            time_span_hours = round((latest_obs_time - earliest_obs_time).total_seconds() / 3600.0, 1)
            hours_evaluated = time_span_hours if time_span_hours > 0.0 else 1.0
        elif len(wave_timestamps) == 1:
            earliest_obs_time = wave_timestamps[0]
            latest_obs_time = wave_timestamps[0]
            hours_evaluated = 1.0
        else:
            earliest_obs_time = None
            latest_obs_time = None
            hours_evaluated = 0.0

        # Operational craft suitability based strictly on wave physics
        if max_wave_m < 1.25:
            operational_feasibility = "FAVORABLE"
            suitability_text = (
                "Wave height meets baseline limits (< 1.25 m). "
                "However, overall vessel or navigation safety CANNOT be claimed based on wave height alone; "
                "wind velocity, gusts, currents, swell period, and vessel seaworthiness must be independently verified."
            )
        elif max_wave_m < 2.5:
            operational_feasibility = "MODERATE / CAUTION"
            suitability_text = (
                "Moderate seas (1.25 m - 2.5 m). Wave steepness and pitching pose hazards for small artisanal craft. "
                "Mechanized commercial trawlers must exercise heightened vigilance; safety clearance is not implied."
            )
        else:
            operational_feasibility = "HAZARDOUS"
            suitability_text = (
                "Rough sea state (Hs >= 2.5 m). Fishing craft deployment is hazardous and strongly discouraged."
            )

        # ----------------------------------------------------------------------
        # 6. Environmental & Biological Fisheries Indicator Processing
        # ----------------------------------------------------------------------
        # SST evaluation
        observed_sst: float | None = None
        latest_sst_rec: EvidenceRecord | None = None
        if fresh_valid_sst:
            latest_sst_rec = fresh_valid_sst[-1]
            if latest_sst_rec.value is not None:
                observed_sst = float(latest_sst_rec.value)

        thermal_eval = evaluate_thermal_suitability(species_lookup, observed_sst)

        # Chlorophyll-a evaluation
        observed_chla: float | None = None
        latest_chla_rec: EvidenceRecord | None = None
        chla_eval: dict[str, Any] = {"status": "MISSING_EVIDENCE", "sub_score": None}
        if fresh_valid_chla:
            latest_chla_rec = fresh_valid_chla[-1]
            if latest_chla_rec.value is not None:
                observed_chla = float(latest_chla_rec.value)
            if observed_chla is not None:
                if 0.2 <= observed_chla <= 2.5:
                    chla_eval = {
                        "status": "OPTIMAL_MESOTROPHIC",
                        "sub_score": 90.0,
                        "rationale": f"Chlorophyll-a ({observed_chla:.2f} mg/m³) indicates productive frontal feeding zone.",
                    }
                elif observed_chla < 0.2:
                    chla_eval = {
                        "status": "LOW_OLIGOTROPHIC",
                        "sub_score": 40.0,
                        "rationale": f"Chlorophyll-a ({observed_chla:.2f} mg/m³) indicates low primary productivity.",
                    }
                else:
                    chla_eval = {
                        "status": "EUTROPHIC_BLOOM_RISK",
                        "sub_score": 45.0,
                        "rationale": f"Chlorophyll-a ({observed_chla:.2f} mg/m³) indicates potential dense algal bloom or hypoxia risk.",
                    }

        # Biomass telemetry evaluation
        observed_biomass: float | None = None
        latest_bio_rec: EvidenceRecord | None = None
        biomass_eval: dict[str, Any] = {"status": "UNVERIFIED", "sub_score": None}
        if fresh_valid_bio:
            latest_bio_rec = fresh_valid_bio[-1]
            if latest_bio_rec.value is not None:
                observed_biomass = float(latest_bio_rec.value)
            if observed_biomass is not None:
                if observed_biomass >= 300.0:
                    biomass_eval = {
                        "status": "HIGH_ABUNDANCE",
                        "sub_score": 95.0,
                        "rationale": f"Measured biomass density ({observed_biomass:.1f} kg/km²) confirms high abundance.",
                    }
                elif observed_biomass >= 100.0:
                    biomass_eval = {
                        "status": "MODERATE_ABUNDANCE",
                        "sub_score": 75.0,
                        "rationale": f"Measured biomass density ({observed_biomass:.1f} kg/km²) confirms moderate abundance.",
                    }
                else:
                    biomass_eval = {
                        "status": "LOW_ABUNDANCE",
                        "sub_score": 40.0,
                        "rationale": f"Measured biomass density ({observed_biomass:.1f} kg/km²) indicates low abundance.",
                    }

        # ----------------------------------------------------------------------
        # 7. Transparent Scoring & Provenance Grounding
        # ----------------------------------------------------------------------
        available_bio_inputs: list[dict[str, Any]] = []
        base_weights = {
            "sea_surface_temperature": 0.35,
            "chlorophyll_a": 0.35,
            "fish_biomass": 0.30,
        }

        if thermal_eval.get("thermal_sub_score") is not None and observed_sst is not None:
            available_bio_inputs.append({
                "variable": "sea_surface_temperature",
                "value": round(observed_sst, 2),
                "unit": "degC",
                "sub_score": thermal_eval["thermal_sub_score"],
                "base_weight": base_weights["sea_surface_temperature"],
                "rationale": thermal_eval["rationale"],
                "source": latest_sst_rec.source if latest_sst_rec else "unknown",
            })

        if chla_eval.get("sub_score") is not None and observed_chla is not None:
            available_bio_inputs.append({
                "variable": "chlorophyll_a",
                "value": round(observed_chla, 2),
                "unit": "mg/m^3",
                "sub_score": chla_eval["sub_score"],
                "base_weight": base_weights["chlorophyll_a"],
                "rationale": chla_eval["rationale"],
                "source": latest_chla_rec.source if latest_chla_rec else "unknown",
            })

        if biomass_eval.get("sub_score") is not None and observed_biomass is not None:
            available_bio_inputs.append({
                "variable": "fish_biomass",
                "value": round(observed_biomass, 2),
                "unit": "kg/km^2",
                "sub_score": biomass_eval["sub_score"],
                "base_weight": base_weights["fish_biomass"],
                "rationale": biomass_eval["rationale"],
                "source": latest_bio_rec.source if latest_bio_rec else "unknown",
            })

        # Rigorous check: VERIFIED requires fresh, validated biological evidence records
        has_verified_fisheries_evidence = (
            biomass_eval.get("status") in ["HIGH_ABUNDANCE", "MODERATE_ABUNDANCE", "LOW_ABUNDANCE"]
            or (chla_eval.get("sub_score") is not None and thermal_eval.get("thermal_sub_score") is not None)
        )

        missing_biological_variables: list[str] = []
        if observed_sst is None:
            missing_biological_variables.append("sea_surface_temperature")
        if observed_chla is None:
            missing_biological_variables.append("chlorophyll_a")
        if observed_biomass is None:
            missing_biological_variables.append("fish_biomass")

        if has_verified_fisheries_evidence and available_bio_inputs:
            total_avail_weight = sum(item["base_weight"] for item in available_bio_inputs)
            composite_score = sum(
                (item["base_weight"] / total_avail_weight) * item["sub_score"]
                for item in available_bio_inputs
            )
            suitability_score = round(composite_score, 1)

            if suitability_score >= 80.0:
                zone_suitability = "FAVORABLE"
            elif suitability_score >= 60.0:
                zone_suitability = "MODERATE"
            elif suitability_score >= 40.0:
                zone_suitability = "MARGINAL"
            else:
                zone_suitability = "UNFAVORABLE"

            agent_status = "success"
            coverage_pct = round((len(available_bio_inputs) / 3.0) * 100.0, 1)
            confidence_level = "HIGH" if len(available_bio_inputs) == 3 else "MODERATE"
            verified_dist_status = "VERIFIED"
            verified_dist_statement = (
                f"Verified fisheries indicators observed: {len(available_bio_inputs)} "
                f"biological and ocean productivity parameter(s) evaluated from genuine evidence records."
            )
            score_rationale = (
                f"Calculated from {len(available_bio_inputs)} verified inputs with dynamically "
                f"normalized weights ({', '.join(item['variable'] for item in available_bio_inputs)}). "
                f"Missing variables ({', '.join(missing_biological_variables) or 'none'}) were not penalized with zeros."
            )
        else:
            # Baseline case: Open-Meteo Marine supplies wave physics only;
            # fisheries evidence is missing or unverified. Never fabricate scores or fish presence.
            suitability_score = None
            zone_suitability = "INSUFFICIENT_EVIDENCE"
            agent_status = "insufficient_evidence"
            coverage_pct = 0.0
            confidence_level = "INSUFFICIENT_EVIDENCE"
            verified_dist_status = "UNVERIFIED"
            verified_dist_statement = (
                "No verified fish distribution or satellite chlorophyll telemetry is available. "
                "Fish locations cannot be guaranteed or invented."
            )
            score_rationale = (
                "Biological suitability score cannot be calculated: direct fish biomass and chlorophyll-a "
                "telemetry are unavailable on the connected provider. ORCA does not generate arbitrary numeric "
                "scores from wave physics alone."
            )

        # ----------------------------------------------------------------------
        # 8. Provenance Metadata Compilation
        # ----------------------------------------------------------------------
        def _build_provenance(rec: EvidenceRecord | None) -> dict[str, Any] | None:
            if not rec:
                return None
            is_rec_forecast = "forecast_data" in (rec.quality_flags or [])
            stale = is_stale(rec, now=now_utc, allow_forecast=is_rec_forecast)
            freshness_status = "missing" if rec.observed_at is None else ("stale" if stale else "valid")
            sensor_desc = (
                rec.metadata.get("sensor_description")
                or rec.metadata.get("sensor_dataset")
                or (
                    "Numerical ocean wave/SST model"
                    if "open_meteo" in rec.source
                    else "Satellite remote sensing sensor"
                )
            )
            req_lat = rec.metadata.get("requested_latitude")
            if req_lat is None:
                req_lat = lat
            req_lon = rec.metadata.get("requested_longitude")
            if req_lon is None:
                req_lon = lon

            is_cached = (
                rec.metadata.get("is_cached_snapshot", False)
                or rec.metadata.get("is_offline_fixture", False)
                or "cached_offline_snapshot" in (rec.quality_flags or [])
                or "offline_fixture" in (rec.quality_flags or [])
            )
            if is_cached:
                provenance_status = "CACHED_OBSERVATION"
            elif stale:
                provenance_status = "STALE_OBSERVATION"
            else:
                provenance_status = "LIVE_VALIDATED"

            return {
                "source": rec.source,
                "source_record_id": rec.source_record_id,
                "evidence_id": rec.evidence_id,
                "observed_at": rec.observed_at.isoformat() if rec.observed_at else None,
                "retrieved_at": rec.retrieved_at.isoformat() if rec.retrieved_at else None,
                "unit": rec.unit,
                "latitude": rec.latitude,
                "longitude": rec.longitude,
                "requested_latitude": req_lat,
                "requested_longitude": req_lon,
                "freshness_status": freshness_status,
                "sensor_description": sensor_desc,
                "quality_flags": rec.quality_flags or [],
                "provenance_status": provenance_status,
            }

        evidence_provenance = {
            "wave_height": _build_provenance(latest_wave_rec),
            "sea_surface_temperature": _build_provenance(latest_sst_rec),
            "chlorophyll_a": _build_provenance(latest_chla_rec),
            "fish_biomass": _build_provenance(latest_bio_rec),
        }

        # ----------------------------------------------------------------------
        # 9. Criteria, Warnings, and Disclaimers Formulation
        # ----------------------------------------------------------------------
        criteria_applied = [
            f"Physical sea state: WMO Code {sea_state['wmo_code']} ({sea_state['category']}).",
            f"Wave conditions: Max wave height {max_wave_m:.2f} m, average {avg_wave_m:.2f} m across {len(valid_heights)} accepted observation(s) spanning {hours_evaluated:.1f} hours.",
            f"Wave physical evaluation: {suitability_text}",
            "Vessel safety rule: Wave height alone does NOT constitute maritime safety clearance or fishing authorization.",
        ]
        if observed_chla is not None:
            criteria_applied.append(f"Satellite ocean color chlorophyll-a observed: {observed_chla:.2f} mg/m^3.")
        else:
            criteria_applied.append("Satellite chlorophyll-a and direct fish biomass telemetry: UNAVAILABLE on current provider.")

        if species_status == "SUPPORTED":
            species_info = species_lookup["species_info"]
            criteria_applied.append(
                f"Target species profile: {species_info['common_name']} ({species_info['scientific_name']}) - "
                f"Optimal SST range {species_info['sst_optimal_min_c']} - {species_info['sst_optimal_max_c']} °C. "
                f"Citation: {species_info['citation']}."
            )
            if observed_sst is not None:
                criteria_applied.append(f"Thermal habitat analysis: {thermal_eval['rationale']}")
        elif species_status == "UNSUPPORTED":
            criteria_applied.append(species_lookup["note"])

        warnings = [
            "CRITICAL: Direct pelagic fish biomass and species distributions are not observed by this provider.",
            "Wave height alone does NOT determine vessel or navigation safety.",
            "Operational feasibility represents strictly physical wave measurements, NOT guaranteed catches or vessel safety clearance.",
        ]

        if any("cached_offline_snapshot" in (r.quality_flags or []) for r in raw_records):
            warnings.append(
                "Offline cached fisheries/satellite snapshot in use; direct live upstream telemetry unavailable."
            )

        if max_wave_m >= 2.5:
            warnings.append(f"Severe wave hazard: Waves reach {max_wave_m:.2f} m.")

        if species_status == "UNSUPPORTED":
            warnings.append(
                f"Unsupported target species '{target_species_raw}'. "
                "Documented thermal preference ranges are unavailable for this species in the registry."
            )

        if rejected_records:
            warnings.append(
                f"{len(rejected_records)} provider observation record(s) rejected as stale or invalid under quality policies."
            )
            if any(r.get("variable") in ["wave_height", "wave_height_m", "hs"] for r in rejected_records):
                warnings.append("One or more wave height records were null or physically invalid and were excluded.")

        # Divergence / conflict warnings between craft operability and biological habitat
        if operational_feasibility == "FAVORABLE" and thermal_eval.get("thermal_suitability") in ("UNFAVORABLE", "UNFAVORABLE (GENERAL)"):
            warnings.append(
                f"CONFLICT / DIVERGENCE: Physical wave conditions are FAVORABLE (< 1.25 m) for craft operation, "
                f"but observed sea surface temperature ({observed_sst:.1f}°C) is UNFAVORABLE (outside thermal range for target species). "
                f"Favorable sea-state does not imply biological habitat suitability or fish availability."
            )

        if operational_feasibility == "HAZARDOUS" and thermal_eval.get("thermal_suitability") in ("OPTIMAL", "FAVORABLE (GENERAL)"):
            warnings.append(
                f"CONFLICT / DIVERGENCE: Sea surface temperature ({observed_sst:.1f}°C) indicates suitable thermal habitat, "
                f"but physical sea state is HAZARDOUS (max wave height {max_wave_m:.2f} m). Vessel safety takes precedence over biological potential."
            )

        # Structured response construction
        observations_payload: dict[str, Any] = {
            "max_wave_height_m": round(max_wave_m, 2),
            "avg_wave_height_m": round(avg_wave_m, 2),
            "sea_state_code": sea_state["wmo_code"],
            "sea_state_category": sea_state["category"],
            "hours_evaluated": hours_evaluated,
            "forecast_window_hours_requested": window_hours,
            "forecast_window_hours_covered": hours_evaluated,
            "earliest_observation_time": earliest_obs_time.isoformat() if earliest_obs_time else None,
            "latest_observation_time": latest_obs_time.isoformat() if latest_obs_time else None,
            "accepted_records_count": len(valid_heights),
            "sea_surface_temperature_c": round(observed_sst, 2) if observed_sst is not None else None,
            "chlorophyll_a_mg_m3": round(observed_chla, 2) if observed_chla is not None else None,
            "fish_biomass_kg_km2": round(observed_biomass, 2) if observed_biomass is not None else None,
            "evidence_records_count": len(records),
            "valid_fresh_records_count": len(fresh_valid_wave) + len(fresh_valid_sst) + len(fresh_valid_chla) + len(fresh_valid_bio),
            "rejected_records_count": len(rejected_records),
            "observation_units": {
                "wave_height": "m",
                "sea_surface_temperature": "degC",
                "chlorophyll_a": "mg/m^3",
                "fish_biomass": "kg/km^2",
            },
            "evidence_provenance": evidence_provenance,
        }

        analysis_payload: dict[str, Any] = {
            "zone_suitability": zone_suitability,
            "operational_feasibility": operational_feasibility,
            "operational_feasibility_scope": "STRICTLY_PHYSICAL_WAVE_CONDITIONS",
            "operational_feasibility_disclaimer": (
                "FAVORABLE operational feasibility reflects strictly physical wave height (< 1.25 m). "
                "It does NOT grant vessel safety clearance, voyage clearance, or fishing operational authorization. "
                "Complete safety evaluation requires checking wind speed, gust hazards, swell period, cross-seas, and vessel seaworthiness via Safety/Risk Agent."
            ),
            "target_species_queried": species_name_queried,
            "target_species_status": species_status,
            "sea_state_category": sea_state["category"],
            "criteria_applied": criteria_applied,
            "vessel_safety_notice": (
                "Wave height is a single physical factor and does NOT determine vessel safety or fishing operational clearance. "
                "Small craft safety requires inspecting wind velocity, wind gusts, currents, swell period, and vessel seaworthiness."
            ),
            "physical_sea_conditions": {
                "max_wave_height_m": round(max_wave_m, 2),
                "avg_wave_height_m": round(avg_wave_m, 2),
                "sea_state_code": sea_state["wmo_code"],
                "sea_state_category": sea_state["category"],
            },
            "environmental_habitat_indicators": {
                "sea_surface_temperature_c": round(observed_sst, 2) if observed_sst is not None else None,
                "thermal_suitability": thermal_eval.get("thermal_suitability"),
                "thermal_evaluation_rationale": thermal_eval.get("rationale"),
                "optimal_range_c": thermal_eval.get("optimal_range_c"),
                "tolerable_range_c": thermal_eval.get("tolerable_range_c"),
                "chlorophyll_a_mg_m3": round(observed_chla, 2) if observed_chla is not None else None,
                "productivity_regime": chla_eval.get("status"),
                "productivity_rationale": chla_eval.get("rationale"),
            },
            "verified_fish_distribution": {
                "status": verified_dist_status,
                "biomass_data_available": has_verified_fisheries_evidence and observed_biomass is not None,
                "catch_probability": None,  # Strictly NEVER fabricated
                "biomass_prediction": None,  # Strictly NEVER fabricated or predicted
                "statement": verified_dist_statement,
                "environmental_suitability_distinction": (
                    "Environmental habitat suitability reflects physical and oceanographic parameters only. "
                    "It does NOT indicate actual fish presence, catch probability, biomass density, or validated prediction."
                ),
            },
            "scoring": {
                "suitability_score": suitability_score,
                "score_scale": "0 to 100 (Higher indicates greater environmental/biological alignment with target fishery)",
                "inputs_evaluated": available_bio_inputs,
                "missing_inputs": missing_biological_variables,
                "evidence_coverage_pct": coverage_pct,
                "confidence_level": confidence_level,
                "scoring_methodology": (
                    "Calculated only over valid, fresh biological and productivity inputs with dynamically normalized weights. "
                    "Missing variables are never converted to zero or assigned arbitrary defaults. "
                    "When biological fisheries data is missing, no numeric score is generated."
                ),
                "rationale": score_rationale,
                "limitations": STANDARD_LIMITATIONS,
            },
            "zone_summary": (
                f"Zone analysis at {loc_name} ({lat:.4f}°N, {lon:.4f}°E): "
                f"Sea state is '{sea_state['category']}' with max wave height {max_wave_m:.2f} m. "
                f"Physical wave condition: {operational_feasibility} (strictly limited to physical wave conditions; NOT vessel safety clearance). "
                f"Biological fisheries evidence: {verified_dist_status.lower()}; direct fish school positions cannot be confirmed. "
                f"Notice: Wave height alone does not constitute vessel safety or sailing clearance."
            ),
            "fish_distribution_disclaimer": (
                "ORCA does not invent or simulate unverified fish coordinates. "
                "Official Potential Fishing Zone (PFZ) advisories require multi-spectral satellite "
                "thermal infrared (SST) and ocean color chlorophyll sensors (e.g. INCOIS/NOAA)."
            ),
            "biological_prediction": self._evaluate_biological_evidence(
                wave_rec=latest_wave_rec or (all_wave_records[-1] if all_wave_records else None),
                sst_rec=latest_sst_rec or (all_sst_records[-1] if all_sst_records else None),
                chla_rec=latest_chla_rec or (all_chla_records[-1] if all_chla_records else None),
                now=now_utc,
                target_species=target_species_raw,
                latitude=lat,
                longitude=lon,
            ),
        }

        is_offline = any(
            "cached_offline_snapshot" in (r.quality_flags or [])
            or "offline_fixture" in (r.quality_flags or [])
            or r.metadata.get("is_cached_snapshot", False)
            or r.metadata.get("is_offline_fixture", False)
            for r in raw_records
        )
        active_mode = "offline_cached" if is_offline else "live"

        def _classify_state(fresh_list: list, all_list: list, var_name: str) -> str:
            if fresh_list:
                rec = fresh_list[-1]
                if any(f in (rec.quality_flags or []) for f in ("cached_offline_snapshot", "offline_fixture")) or rec.metadata.get("is_cached_snapshot"):
                    return "CACHED_OBSERVATION"
                return "LIVE_VALIDATED"
            if all_list:
                rec = all_list[-1]
                if any(f in (rec.quality_flags or []) for f in ("cached_offline_snapshot", "offline_fixture")) or rec.metadata.get("is_cached_snapshot"):
                    return "CACHED_OBSERVATION"
                return "STALE_OBSERVATION"
            if var_name in ("chlorophyll_a", "fish_biomass") and self.fisheries_provider is None:
                return "UNAVAILABLE_PROVIDER"
            return "EMPTY_RESULT"

        provider_states = {
            "wave_height": _classify_state(fresh_valid_wave, all_wave_records, "wave_height"),
            "sea_surface_temperature": _classify_state(fresh_valid_sst, all_sst_records, "sea_surface_temperature"),
            "chlorophyll_a": _classify_state(fresh_valid_chla, all_chla_records, "chlorophyll_a"),
            "fish_biomass": _classify_state(fresh_valid_bio, all_bio_records, "fish_biomass"),
        }

        # Preserved data source information
        data_source_payload: dict[str, Any] = {
            "provider": getattr(self.provider, "provider_name", "open-meteo-marine"),
            "coverage": "Numerical ocean wave model (ECMWF / Meteo-France)",
            "data_limitations": "Lacks direct satellite chlorophyll-a or fish telemetry",
            "active_data_mode": active_mode,
            "is_offline_fixture": is_offline,
            "connected_providers": CONNECTED_PROVIDERS,
            "provider_states": provider_states,
            "contributing_sources": sorted(list(contributing_sources)),
            "missing_providers": MISSING_FISHERIES_PROVIDERS,
            "recommended_integrations": RECOMMENDED_INTEGRATIONS,
            "rejected_records_count": len(rejected_records),
            "rejected_records": rejected_records,
            "rejected_records_reasons": sorted(list({r["reason"] for r in rejected_records})),
            "provenance_summary": (
                f"{len(fresh_valid_wave) + len(fresh_valid_sst) + len(fresh_valid_chla) + len(fresh_valid_bio)} fresh record(s) "
                f"contributed from {len(contributing_sources)} source(s); {len(rejected_records)} record(s) rejected."
            ),
        }

        error_message = (
            "Direct biological fish distribution, biomass, and chlorophyll-a telemetry are unavailable on connected marine provider."
            if agent_status == "insufficient_evidence"
            else None
        )

        return FishingZoneAnalyzeResponse(
            status=agent_status,
            location=location_payload,
            data_source=data_source_payload,
            observations=observations_payload,
            analysis=analysis_payload,
            warnings=warnings,
            error=error_message,
        )
