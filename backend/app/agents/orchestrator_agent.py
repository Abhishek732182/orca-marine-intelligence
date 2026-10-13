"""ORCA Orchestrator Agent (Agent 6).

An evidence-grounded orchestrator that plans, invokes, and synthesizes results from
ORCA's five independent specialist agents (Weather, Ocean, Fishing Zone, Route, Safety/Risk)
using LangGraph and asynchronous parallel execution.

Architectural Guarantees:
- Specialist agents remain fully independent and uncoupled.
- Strictly separates measured provider observations from geodesic estimates and derived models.
- Never invents missing evidence; preserves specialist error and insufficient_evidence statuses.
- Strictly preserves Safety/Risk findings: never downgrades CRITICAL/HIGH risk or interprets missing data as safe.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, cast
from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph

from app.agents.fishing_zone_agent import FishingZoneAgent
from app.agents.ocean_agent import OceanAgent
from app.agents.route_agent import RouteAgent
from app.agents.safety_risk_agent import SafetyRiskAgent
from app.agents.sea_state_rules import classify_sea_state
from app.agents.weather_agent import WeatherAgent
from app.data_sources.ingestion_worker import get_fisheries_worker
from app.agents.mission_planner import plan_mission_request
from app.agents.mission_synthesizer import (
    generate_deterministic_synthesis,
    synthesize_mission_advisory,
)
from app.schemas.agent_schemas import (
    FishingZoneAnalyzeRequest,
    FishingZoneAnalyzeResponse,
    OceanAnalyzeRequest,
    OceanAnalyzeResponse,
    OrchestratorAnalyzeRequest,
    OrchestratorAnalyzeResponse,
    RouteAnalyzeRequest,
    RouteAnalyzeResponse,
    SafetyRiskAnalyzeRequest,
    SafetyRiskAnalyzeResponse,
    WeatherAnalyzeRequest,
    WeatherAnalyzeResponse,
)

LEGAL_DISCLAIMER = (
    "ORCA Decision Support: Synthesized advisory is generated for situational awareness "
    "and operational voyage planning only. Mariners retain sole legal command and responsibility. "
    "Straight-line route distances do not constitute authorized hydrographic navigation tracks. "
    "Direct fish school distributions are unverified. Always verify official government hydrographic notices, "
    "IMD/NOAA marine bulletins, and local port captain clearances before putting to sea."
)


class OrchestratorState(TypedDict, total=False):
    """LangGraph state representation for mission orchestration."""

    # Input request attributes
    latitude: float | None
    longitude: float | None
    origin_latitude: float | None
    origin_longitude: float | None
    location_name: str
    origin_name: str
    forecast_time_window_hours: int
    user_objective: str
    vessel_type: str
    target_species: str | None
    destination_latitude: float | None
    destination_longitude: float | None
    destination_name: str | None
    waypoints: list[dict[str, Any]]
    vessel_speed_knots: float
    wave_height_m: float | None
    wind_speed_knots: float | None
    precipitation_mm: float | None

    # Natural-language and planning fields
    query: str | None
    clarification_needed: bool
    clarification_prompt: str | None
    missing_inputs: list[str]
    descriptive_synthesis: str | None
    generation_mode: str

    # Workflow tracking
    step_progress: list[str]
    planned_agents: list[str]
    attempted_agents: list[str]
    executed_agents: list[str]
    failed_agents: list[str]
    skipped_agents: list[str]

    # Specialist responses (raw dict representation)
    specialist_responses: dict[str, Any]

    # Synthesized intelligence
    measured_observations: dict[str, Any]
    derived_estimates: dict[str, Any]
    composite_safety_risk: dict[str, Any]
    evidence_sources: list[dict[str, Any]]
    timestamps: dict[str, Any]
    warnings: list[str]
    missing_evidence: list[str]
    errors: dict[str, str]
    recommendations: list[str]
    status: str
    summary: str



class OrchestratorAgent:
    """ORCA Agent 6: Master Mission Orchestrator."""

    def __init__(
        self,
        weather_agent: WeatherAgent | None = None,
        ocean_agent: OceanAgent | None = None,
        fishing_zone_agent: FishingZoneAgent | None = None,
        route_agent: RouteAgent | None = None,
        safety_risk_agent: SafetyRiskAgent | None = None,
    ) -> None:
        """Initialize orchestrator with injectable specialist agents."""
        self.weather_agent = weather_agent or WeatherAgent()
        self.ocean_agent = ocean_agent or OceanAgent()
        self.fishing_zone_agent = fishing_zone_agent or FishingZoneAgent(
            fisheries_provider=get_fisheries_worker()
        )
        self.route_agent = route_agent or RouteAgent()
        self.safety_risk_agent = safety_risk_agent or SafetyRiskAgent()
        self.graph = self._build_graph()

    def _build_graph(self):
        """Construct the LangGraph orchestration workflow."""
        builder = StateGraph(cast(Any, OrchestratorState))
        builder.add_node("plan_mission", self._plan_mission_node)
        builder.add_node("execute_specialists", self._execute_specialists_node)
        builder.add_node("synthesize_advisory", self._synthesize_advisory_node)

        builder.add_edge(START, "plan_mission")
        builder.add_conditional_edges(
            "plan_mission",
            self._route_after_planning,
            {
                "execute": "execute_specialists",
                "synthesize": "synthesize_advisory",
            },
        )
        builder.add_edge("execute_specialists", "synthesize_advisory")
        builder.add_edge("synthesize_advisory", END)

        return builder.compile()

    def _route_after_planning(self, state: OrchestratorState) -> str:
        """Route to synthesis immediately if clarification is needed or no agents are planned."""
        if state.get("clarification_needed", False):
            return "synthesize"
        planned = state.get("planned_agents", [])
        if not planned:
            return "synthesize"
        return "execute"

    async def _plan_mission_node(self, state: OrchestratorState) -> dict[str, Any]:
        """Step 1: Determine which specialist agents to invoke based on user objective and query."""
        progress = list(state.get("step_progress", []))
        query = state.get("query")
        plan, mode = await plan_mission_request(query, dict(state))

        clarification_needed = plan.clarification_needed
        clarification_prompt = plan.clarification_prompt
        missing_inputs = list(plan.missing_inputs)

        updates: dict[str, Any] = {
            "user_objective": plan.user_objective,
            "planned_agents": plan.planned_agents,
            "forecast_time_window_hours": plan.forecast_time_window_hours,
            "vessel_type": plan.vessel_type,
            "target_species": plan.target_species or state.get("target_species"),
            "clarification_needed": clarification_needed,
            "clarification_prompt": clarification_prompt,
            "missing_inputs": missing_inputs,
            "generation_mode": mode,
        }

        if plan.origin_latitude is not None and state.get("origin_latitude") is None:
            updates["latitude"] = plan.origin_latitude
            updates["origin_latitude"] = plan.origin_latitude
        if plan.origin_longitude is not None and state.get("origin_longitude") is None:
            updates["longitude"] = plan.origin_longitude
            updates["origin_longitude"] = plan.origin_longitude
        if plan.origin_name and not state.get("origin_name"):
            updates["origin_name"] = plan.origin_name
            updates["location_name"] = plan.origin_name

        if plan.destination_latitude is not None and state.get("destination_latitude") is None:
            updates["destination_latitude"] = plan.destination_latitude
        if plan.destination_longitude is not None and state.get("destination_longitude") is None:
            updates["destination_longitude"] = plan.destination_longitude
        if plan.destination_name and not state.get("destination_name"):
            updates["destination_name"] = plan.destination_name

        if clarification_needed:
            progress.append(
                f"[STEP 1/3] Clarification required ({mode}): missing {', '.join(missing_inputs) or 'parameters'}. "
                f"Halting tool execution to prevent invalid operations."
            )
        else:
            progress.append(
                f"[STEP 1/3] Objective '{plan.user_objective}' ({mode}): planned specialist agents -> {', '.join(plan.planned_agents)}"
            )

        updates["step_progress"] = progress
        return updates

    async def _execute_specialists_node(self, state: OrchestratorState) -> dict[str, Any]:
        """Step 2: Concurrently invoke selected specialist agents in parallel."""
        planned = state.get("planned_agents", [])
        progress = list(state.get("step_progress", []))
        tasks: dict[str, Any] = {}
        specialist_responses: dict[str, Any] = {}
        errors: dict[str, str] = {}
        missing_evidence: list[str] = []

        lat = state.get("latitude")
        lon = state.get("longitude")
        loc_name = state.get("location_name", "Marine Operational Area")
        window_hours = state.get("forecast_time_window_hours", 24)
        vessel_type = state.get("vessel_type", "small_craft")
        target_species = state.get("target_species")

        # 1. Weather Agent task
        if "weather" in planned:
            forecast_days = max(1, min(7, (window_hours + 23) // 24))
            w_req = WeatherAnalyzeRequest(
                latitude=lat,
                longitude=lon,
                location_name=loc_name,
                forecast_days=forecast_days,
            )
            tasks["weather"] = self.weather_agent.analyze(w_req)

        # 2. Ocean Agent task
        if "ocean" in planned:
            if lat is not None and lon is not None:
                o_req = OceanAnalyzeRequest(
                    latitude=lat,
                    longitude=lon,
                    location_name=loc_name,
                    forecast_time_window_hours=window_hours,
                )
                tasks["ocean"] = self.ocean_agent.analyze(o_req)
            else:
                specialist_responses["ocean"] = {
                    "agent": "Ocean Agent",
                    "status": "insufficient_evidence",
                    "error": "Latitude and longitude required for ocean dynamics analysis.",
                    "warnings": ["Coordinates omitted from ocean analysis request."],
                    "observations": {},
                    "analysis": {},
                }
                missing_evidence.append(
                    "Ocean Agent: Coordinates omitted; ocean dynamics cannot be retrieved."
                )

        # 3. Fishing Zone Agent task
        if "fishing_zone" in planned:
            fz_req = FishingZoneAnalyzeRequest(
                latitude=lat,
                longitude=lon,
                location_name=loc_name,
                forecast_time_window_hours=window_hours,
                target_species=target_species,
            )
            tasks["fishing_zone"] = self.fishing_zone_agent.analyze(fz_req)

        # 4. Route Agent task
        if "route" in planned:
            dest_lat = state.get("destination_latitude")
            dest_lon = state.get("destination_longitude")
            orig_lat = state.get("origin_latitude", lat)
            orig_lon = state.get("origin_longitude", lon)
            orig_name = state.get("origin_name", loc_name)
            dest_name = state.get("destination_name") or "Destination Port"

            if dest_lat is not None and dest_lon is not None and orig_lat is not None and orig_lon is not None:
                if orig_lat == dest_lat and orig_lon == dest_lon and not state.get("waypoints"):
                    specialist_responses["route"] = {
                        "agent": "Route Agent",
                        "status": "error",
                        "error": f"Route origin and destination coordinates are identical ({orig_lat}, {orig_lon}). Distinct coordinates required.",
                        "warnings": ["Identical route origin and destination endpoints rejected."],
                        "observations": {},
                        "analysis": {},
                    }
                    errors["route"] = f"Identical origin and destination coordinates ({orig_lat}, {orig_lon})."
                else:
                    waypoints_raw = state.get("waypoints", [])
                    r_req = RouteAnalyzeRequest(
                        origin_latitude=orig_lat,
                        origin_longitude=orig_lon,
                        destination_latitude=dest_lat,
                        destination_longitude=dest_lon,
                        origin_name=orig_name,
                        destination_name=dest_name,
                        waypoints=waypoints_raw,
                        vessel_speed_knots=state.get("vessel_speed_knots", 12.0),
                    )
                    tasks["route"] = self.route_agent.analyze(r_req)
            elif orig_lat is None or orig_lon is None:
                specialist_responses["route"] = {
                    "agent": "Route Agent",
                    "status": "insufficient_evidence",
                    "error": "Origin latitude and longitude required for route passage calculation.",
                    "warnings": ["Origin coordinates omitted from route request."],
                    "observations": {},
                    "analysis": {},
                }
                missing_evidence.append(
                    "Route Agent: Origin coordinates omitted; passage geometry cannot be estimated."
                )
            else:
                # Route planned but destination coordinates omitted
                specialist_responses["route"] = {
                    "agent": "Route Agent",
                    "status": "insufficient_evidence",
                    "error": "Destination latitude and longitude required for route passage calculation.",
                    "warnings": ["Destination coordinates omitted from route request."],
                    "observations": {},
                    "analysis": {},
                }
                missing_evidence.append(
                    "Route Agent: Destination coordinates omitted; passage geometry cannot be estimated."
                )

        # 5. Safety/Risk Agent task
        if "safety_risk" in planned:
            if lat is not None and lon is not None:
                sr_req = SafetyRiskAnalyzeRequest(
                    latitude=lat,
                    longitude=lon,
                    location_name=loc_name,
                    vessel_type=vessel_type,
                    wave_height_m=state.get("wave_height_m"),
                    wind_speed_knots=state.get("wind_speed_knots"),
                    precipitation_mm=state.get("precipitation_mm"),
                )
                tasks["safety_risk"] = self.safety_risk_agent.analyze(sr_req)
            else:
                specialist_responses["safety_risk"] = {
                    "agent": "Safety/Risk Agent",
                    "status": "insufficient_evidence",
                    "error": "Latitude and longitude required for safety and risk assessment.",
                    "warnings": ["Coordinates omitted from safety/risk analysis request."],
                    "observations": {},
                    "analysis": {},
                }
                missing_evidence.append(
                    "Safety/Risk Agent: Coordinates omitted; risk assessment cannot be performed."
                )

        # Parallel dispatch
        agent_names = list(tasks.keys())
        coroutine_list = list(tasks.values())
        results = await asyncio.gather(*coroutine_list, return_exceptions=True)

        for agent_name, result in zip(agent_names, results):
            if isinstance(result, Exception):
                err_msg = f"{type(result).__name__}: {str(result)}"
                errors[agent_name] = err_msg
                specialist_responses[agent_name] = {
                    "agent": agent_name.replace("_", " ").title() + " Agent",
                    "status": "error",
                    "error": err_msg,
                    "warnings": [f"{agent_name} agent failed during execution."],
                    "observations": {},
                    "analysis": {},
                }
            elif hasattr(result, "model_dump"):
                dump = result.model_dump()
                specialist_responses[agent_name] = dump
                if dump.get("status") == "error":
                    errors[agent_name] = dump.get("error") or "Specialist returned error status"
                elif dump.get("status") == "insufficient_evidence":
                    err_text = dump.get("error") or f"{agent_name} reported insufficient evidence"
                    missing_evidence.append(f"{agent_name.replace('_', ' ').title()}: {err_text}")

        attempted = list(tasks.keys())
        failed = [name for name in attempted if name in errors or specialist_responses.get(name, {}).get("status") == "error"]
        skipped = [name for name in planned if name not in tasks]
        executed = [name for name in attempted if name not in failed]

        progress.append(
            f"[STEP 2/3] Parallel execution completed for {len(planned)} planned agents "
            f"({len(attempted)} attempted, {len(executed)} executed, {len(failed)} failed, {len(skipped)} skipped, "
            f"{len(missing_evidence)} missing evidence items)."
        )

        return {
            "attempted_agents": attempted,
            "executed_agents": executed,
            "failed_agents": failed,
            "skipped_agents": skipped,
            "specialist_responses": specialist_responses,
            "errors": errors,
            "missing_evidence": missing_evidence,
            "step_progress": progress,
        }

    async def _synthesize_advisory_node(self, state: OrchestratorState) -> dict[str, Any]:
        """Step 3: Combine specialist responses, partition measured vs derived evidence, and preserve safety risk."""
        responses = state.get("specialist_responses", {})
        errors = dict(state.get("errors", {}))
        missing_evidence = list(state.get("missing_evidence", []))
        progress = list(state.get("step_progress", []))

        lat = state.get("origin_latitude") or state.get("latitude")
        lon = state.get("origin_longitude") or state.get("longitude")
        loc_name = state.get("origin_name") or state.get("location_name", "Marine Operational Area")

        weather = responses.get("weather", {})
        ocean = responses.get("ocean", {})
        fishing_zone = responses.get("fishing_zone", {})
        route = responses.get("route", {})
        safety_risk = responses.get("safety_risk", {})

        # ----------------------------------------------------------------------
        # 1. Measured Numerical Observations (Strictly provider/in-situ observed)
        # ----------------------------------------------------------------------
        w_obs = weather.get("observations", {})
        o_obs = ocean.get("observations", {})
        sr_obs = safety_risk.get("observations", {})

        # Determine significant wave height
        wave_height = state.get("wave_height_m")
        if wave_height is None:
            wave_height = o_obs.get("wave_height_m")
        if wave_height is None:
            wave_height = o_obs.get("max_wave_height_m")
        if wave_height is None:
            wave_height = o_obs.get("latest_wave_height_m")
        if wave_height is None and "ocean" not in responses:
            wave_height = sr_obs.get("wave_height_m")

        # Determine wind speed
        wind_speed_knots = state.get("wind_speed_knots")
        if wind_speed_knots is None:
            wind_speed_knots = w_obs.get("wind_speed_knots")
        if wind_speed_knots is None and "weather" not in responses:
            wind_speed_knots = sr_obs.get("wind_speed_knots")

        wind_direction_deg = w_obs.get("wind_direction_deg")
        temperature_c = w_obs.get("temperature_c")
        precip_mm = state.get("precipitation_mm")
        if precip_mm is None:
            precip_mm = w_obs.get("precipitation_mm")
        if precip_mm is None and "weather" not in responses:
            precip_mm = sr_obs.get("precipitation_mm")

        ocean_analysis = ocean.get("analysis", {})
        wmo_sea_state = ocean_analysis.get("wmo_sea_state") if isinstance(ocean_analysis.get("wmo_sea_state"), dict) else {}
        wmo_code = ocean_analysis.get("sea_state_code")
        if wmo_code is None and isinstance(wmo_sea_state, dict):
            wmo_code = wmo_sea_state.get("code")

        wmo_desc = ocean_analysis.get("description") or ocean_analysis.get("sea_state_category")
        if not wmo_desc and isinstance(wmo_sea_state, dict):
            wmo_desc = wmo_sea_state.get("description") or wmo_sea_state.get("category")

        measured_observations: dict[str, Any] = {
            "wave_height_m": wave_height,
            "wind_speed_knots": wind_speed_knots,
            "wind_direction_deg": wind_direction_deg,
            "temperature_c": temperature_c,
            "precipitation_mm": precip_mm,
            "wmo_sea_state_code": wmo_code,
            "wmo_sea_state_description": wmo_desc,
            "evidence_classification": "MEASURED_OR_NUMERICAL_PROVIDER_OBSERVATION",
            "telemetry_note": (
                "Atmospheric and wave observations sourced from Open-Meteo numerical marine and weather models. "
                "Values represent regional grid estimates and may vary from in-situ buoy telemetry."
            ),
        }

        # ----------------------------------------------------------------------
        # 2. Derived Calculations & Models (Geodesics, Fisheries Models)
        # ----------------------------------------------------------------------
        route_obs = route.get("observations", {})
        route_analysis = route.get("analysis", {})
        fz_analysis = fishing_zone.get("analysis", {})
        route_loc = route.get("location")
        origin_val = route_loc.get("origin") if isinstance(route_loc, dict) else None
        dest_val = route_loc.get("destination") if isinstance(route_loc, dict) else None

        o_name = (origin_val.get("name") if isinstance(origin_val, dict) else (origin_val if isinstance(origin_val, str) else None)) or state.get("origin_name") or loc_name
        o_lat = (origin_val.get("latitude") if isinstance(origin_val, dict) else None) or state.get("origin_latitude") or lat
        o_lon = (origin_val.get("longitude") if isinstance(origin_val, dict) else None) or state.get("origin_longitude") or lon

        d_name = (dest_val.get("name") if isinstance(dest_val, dict) else (dest_val if isinstance(dest_val, str) else None)) or state.get("destination_name")
        d_lat = (dest_val.get("latitude") if isinstance(dest_val, dict) else None) or state.get("destination_latitude")
        d_lon = (dest_val.get("longitude") if isinstance(dest_val, dict) else None) or state.get("destination_longitude")

        derived_estimates: dict[str, Any] = {
            "geodesic_route": {
                "origin_name": o_name,
                "origin_latitude": o_lat,
                "origin_longitude": o_lon,
                "destination_name": d_name,
                "destination_latitude": d_lat,
                "destination_longitude": d_lon,
                "distance_km": route_obs.get("total_distance_km"),
                "distance_nm": route_obs.get("total_distance_nm"),
                "geodesic_distance_km": route_obs.get("total_distance_km"),
                "geodesic_distance_nm": route_obs.get("total_distance_nm"),
                "estimated_transit_hours": route_obs.get("estimated_transit_time_hours") or route_analysis.get("estimated_transit_hours"),
                "waypoint_count": route_obs.get("waypoint_count") or len(state.get("waypoints", [])),
                "route_classification": "GEODESIC_STRAIGHT_LINE_ESTIMATE",
                "is_verified_navigable_route": False,
                "navigability_disclaimer": (
                    "CRITICAL NOTICE: Calculated route represents an estimated straight-line geodesic (Great-Circle) distance only. "
                    "It is NOT a verified, safe, or authorized marine navigational track. "
                    "Does NOT account for shallow bathymetry, shoals, reef hazards, maritime traffic separation schemes (TSS), or land avoidance. "
                    "Mariners must consult official Electronic Navigational Charts (ENC) and hydrographic authorities."
                ),
            },
            "fisheries_suitability": {
                "zone_suitability": fz_analysis.get("zone_suitability", "INSUFFICIENT_EVIDENCE"),
                "operational_feasibility": fz_analysis.get("operational_feasibility", "UNVERIFIED"),
                "operational_feasibility_scope": "STRICTLY_PHYSICAL_WAVE_CONDITIONS",
                "target_species": state.get("target_species") or "General Marine Fisheries",
                "biological_distribution_status": (
                    f"{fz_analysis.get('verified_fish_distribution', {}).get('status', 'UNVERIFIED')}: "
                    f"{fz_analysis.get('verified_fish_distribution', {}).get('statement') or 'Direct fish location, school density, chlorophyll-a, and catch probabilities are unavailable from meteorological models and cannot be inferred.'}"
                ),
                "scoring": fz_analysis.get("scoring"),
                "environmental_suitability_scope": "ENVIRONMENTAL_AND_PHYSICAL_HABITAT_ONLY",
                "environmental_suitability_distinction": (
                    "CRITICAL NOTICE: Evaluated suitability represents environmental habitat conditions only (e.g. water temperature, chlorophyll-a). "
                    "It does NOT indicate actual fish presence, catch probability, biomass volume, or validated predictive catch."
                ),
                "actual_fish_presence": "UNVERIFIED",
                "catch_probability": None,
                "biomass_prediction": None,
                "predictive_accuracy": fz_analysis.get("biological_prediction", {}).get("predictive_accuracy") or "NOT_EVALUABLE",
                "biological_evidence_status": fz_analysis.get("biological_prediction", {}).get("status", "UNVERIFIED"),
                "biological_prediction": fz_analysis.get("biological_prediction"),
            },
            "evidence_classification": "DERIVED_ESTIMATE_AND_MATHEMATICAL_MODEL",
        }

        # ----------------------------------------------------------------------
        # 3. Evidence Sources & Provenance
        # ----------------------------------------------------------------------
        evidence_sources: list[dict[str, Any]] = []

        def _compile_source_record(
            agent_key: str,
            agent_label: str,
            resp: dict[str, Any],
            default_limitations: str,
        ) -> dict[str, Any] | None:
            ds = resp.get("data_source")
            if not ds and not resp:
                return None
            base = dict(ds) if isinstance(ds, dict) else {}
            obs = resp.get("observations", {})
            obs_time = (
                obs.get("latest_observation_time")
                or obs.get("observation_time")
                or obs.get("earliest_observation_time")
                or resp.get("generated_at")
            )
            retrieval_time = resp.get("generated_at") or datetime.now(timezone.utc).isoformat()

            stale_flags = any("stale" in str(w).lower() for w in resp.get("warnings", []))
            if stale_flags:
                freshness_status = "stale"
            elif resp.get("status") == "insufficient_evidence":
                freshness_status = "insufficient_evidence"
            elif resp.get("status") == "error":
                freshness_status = "error"
            else:
                freshness_status = "fresh"

            limitations = (
                base.get("limitations")
                or base.get("data_limitations")
                or default_limitations
            )

            return {
                "agent": agent_label,
                **base,
                "provenance": {
                    "provider": base.get("provider") or base.get("providers_attempted") or "Open-Meteo",
                    "coverage": base.get("coverage", "Regional marine model grid"),
                    "endpoint": base.get("endpoint"),
                },
                "observation_time": obs_time,
                "retrieval_time": retrieval_time,
                "freshness_status": freshness_status,
                "source_limitations": limitations,
            }

        w_src = _compile_source_record(
            "weather",
            "Weather Agent",
            weather,
            "Regional atmospheric model output; lacks micro-scale coastal gusts and in-situ anemometer observations.",
        )
        if w_src:
            evidence_sources.append(w_src)

        o_src = _compile_source_record(
            "ocean",
            "Ocean Agent",
            ocean,
            "Regional wave forecast grid (ECMWF/Meteo-France); does not account for shallow bathymetric shoaling or coastal surf.",
        )
        if o_src:
            evidence_sources.append(o_src)

        fz_src = _compile_source_record(
            "fishing_zone",
            "Fishing Zone Agent",
            fishing_zone,
            "Evaluates physical wave feasibility and thermal preferences only; lacks satellite ocean color (chlorophyll-a) and direct acoustic fish biomass.",
        )
        if fz_src:
            evidence_sources.append(fz_src)

        r_src = _compile_source_record(
            "route",
            "Route Agent",
            route,
            "Straight-line Great-Circle geodesic distance estimate only; does not verify hydrographic navigability, bathymetry, shoals, or traffic separation schemes.",
        )
        if r_src:
            evidence_sources.append(r_src)

        sr_src = _compile_source_record(
            "safety_risk",
            "Safety/Risk Agent",
            safety_risk,
            "Evaluates wave and wind thresholds against nominal craft limits; wave information alone is not vessel safety clearance.",
        )
        if sr_src:
            evidence_sources.append(sr_src)

        timestamps: dict[str, Any] = {
            "orchestrated_at": datetime.now(timezone.utc).isoformat(),
            "weather_timestamp": weather.get("generated_at"),
            "ocean_timestamp": ocean.get("generated_at"),
            "fishing_zone_timestamp": fishing_zone.get("generated_at"),
            "route_timestamp": route.get("generated_at"),
            "safety_risk_timestamp": safety_risk.get("generated_at"),
            "forecast_window_hours": state.get("forecast_time_window_hours", 24),
        }

        # ----------------------------------------------------------------------
        # 4. Warnings Aggregation
        # ----------------------------------------------------------------------
        warnings: list[str] = []
        for agent_key in ["weather", "ocean", "fishing_zone", "route", "safety_risk"]:
            resp = responses.get(agent_key, {})
            agent_warns = resp.get("warnings", [])
            if isinstance(agent_warns, list):
                for w in agent_warns:
                    if w and w not in warnings:
                        warnings.append(w)

        # Explicit validation: detect discrepancies between measured wave height and reported WMO code
        reported_code = wmo_code
        if wave_height is not None and reported_code is not None:
            expected_sea_state = classify_sea_state(wave_height)
            expected_code = expected_sea_state.get("wmo_code")
            if expected_code is not None and expected_code != reported_code:
                wmo_desc_label = wmo_desc or "reported WMO description"
                discrepancy_msg = (
                    f"Observation discrepancy: Reported wave height of {wave_height:.2f} m "
                    f"does not match reported WMO Sea State Code {reported_code} ({wmo_desc_label}). "
                    f"Under WMO Code Table 3700, {wave_height:.2f} m corresponds to "
                    f"Code {expected_code} ({expected_sea_state.get('category')}: {expected_sea_state.get('description')}). "
                    f"Preserving provider evidence while flagging classification conflict."
                )
                if discrepancy_msg not in warnings:
                    warnings.append(discrepancy_msg)
                measured_observations["wmo_discrepancy_warning"] = discrepancy_msg


        # ----------------------------------------------------------------------
        # 5. Composite Safety & Risk (STRICT PRESERVATION RULES)
        # ----------------------------------------------------------------------
        sr_analysis = safety_risk.get("analysis", {})
        raw_risk_cat = sr_analysis.get("risk_category")
        raw_risk_score = sr_analysis.get("risk_score")
        sr_reasons = sr_analysis.get("risk_reasons", [])
        sr_recs = sr_analysis.get("recommendations", [])

        # Safety Enforcement:
        # Rule A: If safety_risk agent reported CRITICAL, composite is strictly CRITICAL.
        # Rule B: If safety_risk agent reported HIGH, composite is strictly HIGH.
        # Rule C: If safety_risk agent reported INSUFFICIENT EVIDENCE or errored, NEVER LOW!
        # Rule D: If wave or wind evidence is missing, composite CANNOT be LOW or safe.
        is_safety_agent_error = "safety_risk" in errors or safety_risk.get("status") == "error"
        is_safety_insufficient = safety_risk.get("status") == "insufficient_evidence"

        if raw_risk_cat == "CRITICAL":
            composite_risk_cat = "CRITICAL"
            composite_risk_score = raw_risk_score or 90
            safety_status = "CRITICAL HAZARD DETECTED"
        elif raw_risk_cat == "HIGH":
            composite_risk_cat = "HIGH"
            composite_risk_score = raw_risk_score or 70
            safety_status = "HIGH HAZARD DETECTED"
        elif is_safety_agent_error or is_safety_insufficient or (wave_height is None and wind_speed_knots is None):
            composite_risk_cat = "UNKNOWN / INSUFFICIENT EVIDENCE"
            composite_risk_score = None
            safety_status = "SAFETY EVIDENCE INCOMPLETE"
            if "Absence of data does NOT imply safe navigation." not in warnings:
                warnings.append("Missing marine telemetry. Never interpret absence of observations as safe conditions.")
        elif raw_risk_cat == "MODERATE":
            composite_risk_cat = "MODERATE"
            composite_risk_score = raw_risk_score or 45
            safety_status = "MODERATE SEA STATE"
        elif raw_risk_cat == "LOW":
            # Extra guard: verify that we actually have positive evidence
            if wave_height is None:
                composite_risk_cat = "UNKNOWN / INSUFFICIENT EVIDENCE"
                composite_risk_score = None
                safety_status = "SAFETY EVIDENCE INCOMPLETE (MISSING WAVE TELEMETRY)"
                warnings.append("Wave telemetry unavailable; cannot certify LOW risk.")
            else:
                composite_risk_cat = "LOW"
                composite_risk_score = raw_risk_score or 15
                safety_status = "FAVORABLE OPERATING CONDITIONS"
        else:
            composite_risk_cat = "UNKNOWN / INSUFFICIENT EVIDENCE"
            composite_risk_score = None
            safety_status = "SAFETY UNVERIFIED"

        composite_safety_risk: dict[str, Any] = {
            "risk_category": composite_risk_cat,
            "risk_score": composite_risk_score,
            "status_headline": safety_status,
            "vessel_type_assessed": state.get("vessel_type", "small_craft"),
            "risk_reasons": sr_reasons if sr_reasons else [
                "Marine hazard evaluation based on available wave height, wind speed, and vessel operational tolerances."
            ],
            "preservation_guarantee": (
                "Strict Safety Assurance: Critical hazard categories are never degraded. "
                "Missing telemetry is strictly classified as unverified and never treated as calm."
            ),
            "wave_clearance_notice": (
                "Wave height is a single sea-state parameter and does NOT constitute vessel safety clearance. "
                "Small craft and commercial vessel safety requires evaluating wind velocity, wind gusts, "
                "wave steepness, swell direction, tidal streams, currents, and vessel seaworthiness."
            ),
        }

        # ----------------------------------------------------------------------
        # 6. Actionable Recommendations Formulation
        # ----------------------------------------------------------------------
        recommendations: list[str] = []
        if composite_risk_cat == "CRITICAL":
            recommendations.append("DANGER: Suspend all maritime operations immediately. Seek sheltered anchorage or remain in port.")
        elif composite_risk_cat == "HIGH":
            recommendations.append("HIGH RISK: Small craft and unmechanized vessels must remain ashore. Commercial vessels operate with extreme vigilance.")
        elif composite_risk_cat == "UNKNOWN / INSUFFICIENT EVIDENCE":
            recommendations.append(
                "EVIDENCE INCOMPLETE: Marine or atmospheric observations are missing. "
                "Do NOT presume calm conditions. Confirm in-situ status via harbor master or marine VHF radio."
            )
        elif composite_risk_cat == "MODERATE":
            recommendations.append("CAUTION: Exercise watchfulness for sudden wave squalls or shifting winds.")
        else:
            recommendations.append("Favorable conditions observed for designated vessel type within current forecast envelope.")

        # Add specialist recommendations if available
        if sr_recs:
            for rec in sr_recs:
                if rec not in recommendations:
                    recommendations.append(rec)

        if "route" in state.get("planned_agents", []) and route.get("status") == "success":
            recommendations.append(
                "Passage Planning: Route is an estimated Great-Circle geodesic distance only. "
                "Vessel masters must verify safe water depths, shoals, TSS lanes, and chart hazards on authorized ENCs before sailing."
            )

        if "fishing_zone" in state.get("planned_agents", []) and fz_analysis.get("zone_suitability"):
            recommendations.append(
                f"Fisheries Note: Operational wave feasibility is rated {fz_analysis.get('operational_feasibility', 'UNVERIFIED')}. "
                "Direct biological fish distributions remain INSUFFICIENT_EVIDENCE; confirm via local fisheries reports."
            )

        # ----------------------------------------------------------------------
        # 7. Overall Mission Status & Summary
        # ----------------------------------------------------------------------
        planned_count = len(state.get("planned_agents", []))
        error_count = len(errors)

        if state.get("clarification_needed", False):
            mission_status = "clarification_needed"
            clarification_prompt = state.get("clarification_prompt") or "Clarification required: essential parameters are missing."
            descriptive_synthesis = generate_deterministic_synthesis(
                location_name=loc_name,
                latitude=lat,
                longitude=lon,
                user_objective=state.get("user_objective", "general_maritime"),
                vessel_type=state.get("vessel_type", "small_craft"),
                measured_observations={},
                derived_estimates={},
                composite_safety_risk={
                    "risk_category": "UNKNOWN / INSUFFICIENT EVIDENCE",
                    "status_headline": "PARAMETERS INCOMPLETE",
                },
                warnings=warnings,
                missing_evidence=list(state.get("missing_inputs", [])),
                errors=errors,
                recommendations=["Provide verified coordinates or port destinations before putting to sea."],
                clarification_needed=True,
                clarification_prompt=clarification_prompt,
            )
            progress.append("[STEP 3/3] Clarification requested -> status='clarification_needed'.")
            return {
                "status": mission_status,
                "summary": descriptive_synthesis,
                "descriptive_synthesis": descriptive_synthesis,
                "generation_mode": state.get("generation_mode", "deterministic"),
                "clarification_needed": True,
                "clarification_prompt": clarification_prompt,
                "missing_inputs": state.get("missing_inputs", []),
                "measured_observations": {},
                "derived_estimates": {},
                "composite_safety_risk": {
                    "risk_category": "UNKNOWN / INSUFFICIENT EVIDENCE",
                    "status_headline": "PARAMETERS INCOMPLETE",
                    "preservation_guarantee": "Never invent telemetry when inputs are missing.",
                },
                "evidence_sources": [],
                "timestamps": timestamps,
                "warnings": warnings,
                "missing_evidence": list(state.get("missing_inputs", [])),
                "errors": errors,
                "recommendations": ["Specify geographical coordinates (latitude and longitude) to proceed."],
                "legal_disclaimer": LEGAL_DISCLAIMER,
                "step_progress": progress,
            }

        if error_count == planned_count and planned_count > 0:
            mission_status = "error"
        elif error_count > 0:
            mission_status = "partial_failure"
        elif ocean.get("status") == "insufficient_evidence" or composite_risk_cat == "UNKNOWN / INSUFFICIENT EVIDENCE":
            mission_status = "insufficient_evidence"
        else:
            mission_status = "success"

        # Generate evidence-grounded descriptive synthesis
        descriptive_synthesis, synth_mode = await synthesize_mission_advisory(
            location_name=loc_name,
            latitude=lat,
            longitude=lon,
            user_objective=state.get("user_objective", "general_maritime"),
            vessel_type=state.get("vessel_type", "small_craft"),
            measured_observations=measured_observations,
            derived_estimates=derived_estimates,
            composite_safety_risk=composite_safety_risk,
            warnings=warnings,
            missing_evidence=missing_evidence,
            errors=errors,
            recommendations=recommendations,
            clarification_needed=False,
        )

        progress.append(
            f"[STEP 3/3] Mission synthesis complete ({synth_mode}) -> status='{mission_status}', composite_risk='{composite_risk_cat}'."
        )

        return {
            "status": mission_status,
            "summary": descriptive_synthesis,
            "descriptive_synthesis": descriptive_synthesis,
            "generation_mode": synth_mode,
            "clarification_needed": False,
            "clarification_prompt": None,
            "missing_inputs": [],
            "measured_observations": measured_observations,
            "derived_estimates": derived_estimates,
            "composite_safety_risk": composite_safety_risk,
            "evidence_sources": evidence_sources,
            "timestamps": timestamps,
            "warnings": warnings,
            "missing_evidence": missing_evidence,
            "errors": errors,
            "recommendations": recommendations,
            "legal_disclaimer": LEGAL_DISCLAIMER,
            "step_progress": progress,
        }

    async def analyze(self, request: OrchestratorAnalyzeRequest) -> OrchestratorAnalyzeResponse:
        """Execute the LangGraph orchestration workflow and return validated response."""
        query_text = request.query or request.message
        lat = request.origin_latitude if request.origin_latitude is not None else request.latitude
        lon = request.origin_longitude if request.origin_longitude is not None else request.longitude
        loc_name = request.origin_name or request.location_name or "Marine Operational Area"

        if not query_text:
            if lat is None or lon is None:
                raise ValueError("Origin latitude and longitude are required.")
            if not -90.0 <= lat <= 90.0 or not -180.0 <= lon <= 180.0:
                raise ValueError(f"Invalid origin coordinates: lat={lat}, lon={lon}")
        else:
            if lat is not None and not -90.0 <= lat <= 90.0:
                raise ValueError(f"Invalid origin coordinates: lat={lat}")
            if lon is not None and not -180.0 <= lon <= 180.0:
                raise ValueError(f"Invalid origin coordinates: lon={lon}")

        initial_state: OrchestratorState = {
            "latitude": lat,
            "longitude": lon,
            "origin_latitude": lat,
            "origin_longitude": lon,
            "location_name": loc_name,
            "origin_name": loc_name,
            "forecast_time_window_hours": request.forecast_time_window_hours,
            "user_objective": request.user_objective,
            "vessel_type": request.vessel_type,
            "target_species": request.target_species,
            "destination_latitude": request.destination_latitude,
            "destination_longitude": request.destination_longitude,
            "destination_name": request.destination_name,
            "waypoints": [w.model_dump() for w in request.waypoints],
            "vessel_speed_knots": request.vessel_speed_knots,
            "wave_height_m": request.wave_height_m,
            "wind_speed_knots": request.wind_speed_knots,
            "precipitation_mm": request.precipitation_mm,
            "query": query_text,
            "step_progress": [],
            "specialist_responses": {},
            "errors": {},
            "missing_evidence": [],
        }

        final_state = await self.graph.ainvoke(initial_state)

        final_lat = final_state.get("origin_latitude") if final_state.get("origin_latitude") is not None else final_state.get("latitude", lat)
        final_lon = final_state.get("origin_longitude") if final_state.get("origin_longitude") is not None else final_state.get("longitude", lon)
        final_loc_name = final_state.get("origin_name") or final_state.get("location_name") or loc_name
        dest_lat = final_state.get("destination_latitude", request.destination_latitude)
        dest_lon = final_state.get("destination_longitude", request.destination_longitude)
        dest_name = final_state.get("destination_name", request.destination_name)

        location_dict = {
            "location_name": final_loc_name,
            "latitude": final_lat,
            "longitude": final_lon,
            "origin_latitude": final_lat,
            "origin_longitude": final_lon,
            "origin_name": final_loc_name,
            "destination_latitude": dest_lat,
            "destination_longitude": dest_lon,
            "destination_name": dest_name,
            "origin": {
                "name": final_loc_name,
                "latitude": final_lat,
                "longitude": final_lon,
            } if final_lat is not None and final_lon is not None else None,
            "destination": {
                "name": dest_name or "Destination Port",
                "latitude": dest_lat,
                "longitude": dest_lon,
            } if dest_lat is not None and dest_lon is not None else None,
        }

        plan_dict = {
            "user_objective": final_state.get("user_objective", request.user_objective),
            "planned_agents": final_state.get("planned_agents", []),
            "attempted_agents": final_state.get("attempted_agents", []),
            "executed_agents": final_state.get("executed_agents", []),
            "failed_agents": final_state.get("failed_agents", []),
            "skipped_agents": final_state.get("skipped_agents", []),
            "step_progress": final_state.get("step_progress", []),
        }

        return OrchestratorAnalyzeResponse(
            status=final_state.get("status", "success"),
            user_objective=final_state.get("user_objective", request.user_objective),
            location=location_dict,
            plan=plan_dict,
            summary=final_state.get("summary", "Mission synthesis completed."),
            descriptive_synthesis=final_state.get("descriptive_synthesis"),
            generation_mode=final_state.get("generation_mode", "deterministic"),
            clarification_needed=final_state.get("clarification_needed", False),
            clarification_prompt=final_state.get("clarification_prompt"),
            missing_inputs=final_state.get("missing_inputs", []),
            composite_safety_risk=final_state.get("composite_safety_risk", {}),
            measured_observations=final_state.get("measured_observations", {}),
            derived_estimates=final_state.get("derived_estimates", {}),
            individual_agent_results=final_state.get("specialist_responses", {}),
            evidence_sources=final_state.get("evidence_sources", []),
            timestamps=final_state.get("timestamps", {}),
            warnings=final_state.get("warnings", []),
            missing_evidence=final_state.get("missing_evidence", []),
            errors=final_state.get("errors", {}),
            recommendations=final_state.get("recommendations", []),
            legal_disclaimer=final_state.get("legal_disclaimer", LEGAL_DISCLAIMER),
        )
