"""Structured Mission Planning for ORCA LangGraph Orchestrator.

Extracts intent, location, origin/destination, forecast window, vessel parameters,
target species, and requested analyses from natural-language or structured requests.
Validates all plans against an explicit Pydantic schema and a strict allowlist of
the five independent specialist agents.
Asks for clarification when essential information is missing without inventing coordinates.
Supports LLM interpretation with a rigorous deterministic fallback.
"""

import re
from typing import Any
from pydantic import BaseModel, Field, field_validator

from app.agents.llm_client import call_json_llm

# Strict allowlist of the five independent specialist agents
ALLOWED_SPECIALIST_AGENTS = frozenset([
    "weather",
    "ocean",
    "fishing_zone",
    "route",
    "safety_risk",
])

# Canonical mapping for specialist agent names and tool aliases
SPECIALIST_ALIAS_MAP = {
    "weather": "weather",
    "weather_agent": "weather",
    "invoke_weather_agent": "weather",
    "weather agent": "weather",
    "ocean": "ocean",
    "ocean_agent": "ocean",
    "invoke_ocean_agent": "ocean",
    "ocean agent": "ocean",
    "fishing": "fishing_zone",
    "fishing_zone": "fishing_zone",
    "fishing_zone_agent": "fishing_zone",
    "invoke_fishing_zone_agent": "fishing_zone",
    "fishing zone agent": "fishing_zone",
    "route": "route",
    "route_agent": "route",
    "invoke_route_agent": "route",
    "route agent": "route",
    "geospatial": "route",
    "safety": "safety_risk",
    "safety_risk": "safety_risk",
    "safety_risk_agent": "safety_risk",
    "invoke_safety_risk_agent": "safety_risk",
    "safety agent": "safety_risk",
    "safety/risk": "safety_risk",
    "safety/risk agent": "safety_risk",
}

# Major known marine hubs in the Indian Ocean / Arabian Sea region
KNOWN_PORTS: dict[str, tuple[float, float, str]] = {
    "mumbai": (18.95, 72.82, "Mumbai Port"),
    "goa": (15.0, 72.0, "Goa Sector"),
    "cochin": (9.97, 76.28, "Cochin Harbor"),
    "kochi": (9.97, 76.28, "Cochin Harbor"),
    "mangalore": (12.92, 74.82, "New Mangalore Port"),
    "chennai": (13.08, 80.29, "Chennai Port"),
}

VALID_VESSEL_TYPES = frozenset(["small_craft", "trawler", "commercial_cargo", "passenger"])
VALID_OBJECTIVES = frozenset(["general_maritime", "fishing", "passage_planning", "safety_check", "all"])


class StructuredPlanSchema(BaseModel):
    """Explicit schema for model-generated and deterministic mission plans."""

    user_objective: str = Field(
        default="general_maritime",
        description="Mission objective ('general_maritime', 'fishing', 'passage_planning', 'safety_check', 'all')",
    )
    location_name: str | None = Field(default=None, max_length=200)
    origin_name: str | None = Field(default=None, max_length=200)
    origin_latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    origin_longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    destination_name: str | None = Field(default=None, max_length=200)
    destination_latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    destination_longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    forecast_time_window_hours: int = Field(default=24, ge=1, le=168)
    vessel_type: str = Field(default="small_craft")
    target_species: str | None = Field(default=None, max_length=100)
    planned_agents: list[str] = Field(default_factory=list)
    requested_analyses: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    clarification_needed: bool = False
    clarification_prompt: str | None = None

    @field_validator("planned_agents", mode="after")
    @classmethod
    def validate_allowlist(cls, agents: list[str]) -> list[str]:
        """Strictly enforce the allowlist of the five specialist agents."""
        sanitized: list[str] = []
        for a in agents:
            if not isinstance(a, str):
                continue
            canonical = SPECIALIST_ALIAS_MAP.get(a.strip().lower())
            if canonical and canonical in ALLOWED_SPECIALIST_AGENTS:
                if canonical not in sanitized:
                    sanitized.append(canonical)
        return sanitized

    @field_validator("vessel_type", mode="after")
    @classmethod
    def validate_vessel(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if v_clean in VALID_VESSEL_TYPES:
            return v_clean
        return "small_craft"

    @field_validator("user_objective", mode="after")
    @classmethod
    def validate_objective(cls, obj: str) -> str:
        o_clean = obj.strip().lower()
        if o_clean in VALID_OBJECTIVES:
            return o_clean
        return "general_maritime"


def _extract_coordinates_regex(text: str) -> list[tuple[float, float]]:
    """Extract latitude/longitude pairs from free text."""
    coord_pattern = r"(-?\d+(?:\.\d+)?)\s*°?\s*([NSns])?\s*,\s*(-?\d+(?:\.\d+)?)\s*°?\s*([EWew])?"
    pairs: list[tuple[float, float]] = []
    for m in re.finditer(coord_pattern, text):
        try:
            lat = float(m.group(1))
            if m.group(2) and m.group(2).upper() == "S":
                lat = -lat
            lon = float(m.group(3))
            if m.group(4) and m.group(4).upper() == "W":
                lon = -lon
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                pairs.append((lat, lon))
        except (ValueError, TypeError):
            continue
    return pairs


def _extract_location_and_endpoints(
    text: str,
) -> tuple[float | None, float | None, str | None, float | None, float | None, str | None]:
    """Deterministically parse origin and destination from text."""
    lower = text.lower()
    orig_lat: float | None = None
    orig_lon: float | None = None
    orig_name: str | None = None
    dest_lat: float | None = None
    dest_lon: float | None = None
    dest_name: str | None = None

    from_match = re.search(r"\bfrom\s+(.+?)(?:\s+to\b|$)", lower)
    to_match = re.search(r"\bto\s+(.+?)(?:\s+from\b|$)", lower)
    between_match = re.search(r"\bbetween\s+(.+?)\s+and\s+(.+?)(?:\b|$)", lower)

    if from_match:
        from_text = from_match.group(1).strip()
        fc = _extract_coordinates_regex(from_text)
        if fc:
            orig_lat, orig_lon = fc[0]
        for key, (plat, plon, pname) in KNOWN_PORTS.items():
            if key in from_text:
                orig_name = pname
                if orig_lat is None:
                    orig_lat, orig_lon = plat, plon
                break

    if between_match:
        from_text = between_match.group(1).strip()
        to_text = between_match.group(2).strip()
        fc = _extract_coordinates_regex(from_text)
        if fc:
            orig_lat, orig_lon = fc[0]
        for key, (plat, plon, pname) in KNOWN_PORTS.items():
            if key in from_text:
                orig_name = pname
                if orig_lat is None:
                    orig_lat, orig_lon = plat, plon
                break
        tc = _extract_coordinates_regex(to_text)
        if tc:
            dest_lat, dest_lon = tc[0]
        for key, (plat, plon, pname) in KNOWN_PORTS.items():
            if key in to_text:
                dest_name = pname
                if dest_lat is None:
                    dest_lat, dest_lon = plat, plon
                break

    elif to_match:
        to_text = to_match.group(1).strip()
        tc = _extract_coordinates_regex(to_text)
        if tc:
            dest_lat, dest_lon = tc[0]
        for key, (plat, plon, pname) in KNOWN_PORTS.items():
            if key in to_text:
                dest_name = pname
                if dest_lat is None:
                    dest_lat, dest_lon = plat, plon
                break
        pre_to = lower[:to_match.start()]
        pre_match = re.search(r"(?:route\s+|advisory\s+for:\s*|passage\s+|from\s+|^)([\w\s.,°\(\)\-]+?)$", pre_to)
        if pre_match:
            cand = pre_match.group(1).strip()
            fc = _extract_coordinates_regex(cand)
            if fc:
                orig_lat, orig_lon = fc[0]
            for key, (plat, plon, pname) in KNOWN_PORTS.items():
                if key in cand:
                    orig_name = pname
                    if orig_lat is None:
                        orig_lat, orig_lon = plat, plon
                    break

    all_coords = _extract_coordinates_regex(text)
    if len(all_coords) >= 2 and (orig_lat is None or dest_lat is None):
        if orig_lat is None and dest_lat is None:
            orig_lat, orig_lon = all_coords[0]
            dest_lat, dest_lon = all_coords[1]
        elif orig_lat is None:
            cand = next((c for c in all_coords if c != (dest_lat, dest_lon)), all_coords[0])
            orig_lat, orig_lon = cand
        elif dest_lat is None:
            cand = next((c for c in all_coords if c != (orig_lat, orig_lon)), all_coords[1])
            dest_lat, dest_lon = cand
    elif len(all_coords) == 1 and orig_lat is None and dest_lat is None:
        orig_lat, orig_lon = all_coords[0]

    for key, (plat, plon, pname) in KNOWN_PORTS.items():
        if key in lower:
            is_same_as_orig = orig_lat is not None and abs(plat - orig_lat) < 0.05 and abs(plon - orig_lon) < 0.05
            is_same_as_dest = dest_lat is not None and abs(plat - dest_lat) < 0.05 and abs(plon - dest_lon) < 0.05

            if is_same_as_orig:
                orig_name = pname
            elif is_same_as_dest:
                dest_name = pname
            elif orig_name is None and orig_lat is None:
                orig_name = pname
                orig_lat, orig_lon = plat, plon
            elif dest_name is None and dest_lat is None and pname != orig_name and (plat != orig_lat or plon != orig_lon):
                dest_name = pname
                dest_lat, dest_lon = plat, plon

    return orig_lat, orig_lon, orig_name, dest_lat, dest_lon, dest_name


def deterministic_plan_mission(
    query: str | None,
    structured_params: dict[str, Any],
) -> StructuredPlanSchema:
    """Deterministic planning fallback without model hallucinations."""
    text = (query or structured_params.get("user_objective") or "").strip()
    lower = text.lower()

    # 1. Coordinates & locations
    s_lat = structured_params.get("origin_latitude") or structured_params.get("latitude")
    s_lon = structured_params.get("origin_longitude") or structured_params.get("longitude")
    s_orig_name = structured_params.get("origin_name") or structured_params.get("location_name")

    s_dest_lat = structured_params.get("destination_latitude")
    s_dest_lon = structured_params.get("destination_longitude")
    s_dest_name = structured_params.get("destination_name")

    t_olat, t_olon, t_oname, t_dlat, t_dlon, t_dname = _extract_location_and_endpoints(text)

    orig_lat = s_lat if s_lat is not None else t_olat
    orig_lon = s_lon if s_lon is not None else t_olon
    orig_name = s_orig_name or t_oname or ("Offshore Sector" if orig_lat is not None else None)

    dest_lat = s_dest_lat if s_dest_lat is not None else t_dlat
    dest_lon = s_dest_lon if s_dest_lon is not None else t_dlon
    dest_name = s_dest_name or t_dname

    # 2. Forecast window
    window = structured_params.get("forecast_time_window_hours", 24)
    win_match = re.search(r"(\d+)\s*(?:h|hrs|hours?)\s*(?:forecast|window)?", lower)
    if win_match:
        try:
            window = max(1, min(168, int(win_match.group(1))))
        except ValueError:
            pass

    # 3. Vessel type
    vessel = structured_params.get("vessel_type", "small_craft")
    if "trawler" in lower or "mechanized" in lower:
        vessel = "trawler"
    elif "cargo" in lower or "commercial" in lower or "merchant" in lower:
        vessel = "commercial_cargo"
    elif "passenger" in lower or "ferry" in lower:
        vessel = "passenger"
    elif "small craft" in lower or "skiff" in lower:
        vessel = "small_craft"

    # 4. Target species
    target_species = structured_params.get("target_species")
    if not target_species:
        if "mackerel" in lower:
            target_species = "Mackerel"
        elif "tuna" in lower:
            target_species = "Tuna"
        elif "sardine" in lower:
            target_species = "Sardine"

    # 5. Objective & Specialist Agent Selection
    explicit_obj = structured_params.get("user_objective")
    has_dest = dest_lat is not None and dest_lon is not None
    is_route_text = any(w in lower for w in ["route", "passage", "transit", "distance", "bearing", "waypoint", "voyage"])
    is_fishing_text = any(w in lower for w in ["fish", "fishery", "fishing", "catch", "mackerel", "tuna"])
    is_safety_text = any(w in lower for w in ["safety", "risk", "safe to sail", "gale", "hazard"])
    is_all_text = ("all" in lower and "agent" in lower) or ("five" in lower and "agent" in lower) or explicit_obj == "all"

    if is_all_text:
        obj = "all"
        planned = ["weather", "ocean", "fishing_zone", "route", "safety_risk"]
    elif explicit_obj == "fishing" or is_fishing_text:
        obj = "fishing"
        planned = ["weather", "ocean", "fishing_zone", "safety_risk"]
        if has_dest or is_route_text:
            planned.append("route")
    elif explicit_obj == "passage_planning" or (is_route_text and not is_fishing_text):
        obj = "passage_planning"
        planned = ["weather", "ocean", "route", "safety_risk"]
    elif explicit_obj == "safety_check" or (is_safety_text and not is_fishing_text and not is_route_text):
        obj = "safety_check"
        planned = ["weather", "ocean", "safety_risk"]
    else:
        obj = explicit_obj if explicit_obj in VALID_OBJECTIVES else "general_maritime"
        planned = ["weather", "ocean", "fishing_zone", "safety_risk"]
        if has_dest:
            planned.append("route")

    # 6. Missing Inputs & Clarification Enforcement
    missing_inputs: list[str] = []
    clarification_needed = False
    clarification_prompt = None

    # Check origin coordinates
    if orig_lat is None or orig_lon is None:
        missing_inputs.append("origin_coordinates")
        clarification_needed = True
        clarification_prompt = (
            "Marine intelligence analysis requires geographical coordinates. "
            "Please specify origin latitude and longitude (e.g. 15.0°N, 72.0°E) or a recognized port name (such as Goa or Mumbai)."
        )

    # Check destination for passage planning
    elif obj == "passage_planning" or ("route" in planned and is_route_text):
        if dest_lat is None or dest_lon is None:
            missing_inputs.append("destination_coordinates")
            if query:
                clarification_needed = True
                clarification_prompt = (
                    "Passage planning requires a destination endpoint. "
                    "Please specify destination latitude and longitude (e.g. 18.95°N, 72.82°E) or destination port name."
                )
        elif orig_lat == dest_lat and orig_lon == dest_lon:
            missing_inputs.append("distinct_route_endpoints")
            if query:
                clarification_needed = True
                clarification_prompt = (
                    f"Route origin and destination coordinates are identical ({orig_lat:.4f}, {orig_lon:.4f}). "
                    "A valid marine route calculation requires distinct origin and destination coordinates."
                )

    return StructuredPlanSchema(
        user_objective=obj,
        location_name=orig_name or "Marine Operational Area",
        origin_name=orig_name or "Marine Operational Area",
        origin_latitude=orig_lat,
        origin_longitude=orig_lon,
        destination_name=dest_name,
        destination_latitude=dest_lat,
        destination_longitude=dest_lon,
        forecast_time_window_hours=window,
        vessel_type=vessel,
        target_species=target_species,
        planned_agents=planned,
        requested_analyses=planned,
        missing_inputs=missing_inputs,
        clarification_needed=clarification_needed,
        clarification_prompt=clarification_prompt,
    )


PLANNING_SYSTEM_PROMPT = """You are the ORCA Mission Planning Interpreter for maritime operations.
Interpret user maritime requests and extract structured mission parameters.
STRICT RELIABILITY & ALLOWLIST RULES:
1. ALLOWED SPECIALIST AGENTS: You may ONLY plan from this exact list: 'weather', 'ocean', 'fishing_zone', 'route', 'safety_risk'.
   NEVER include any other tool or agent name. Never generate arbitrary code.
2. NEVER INVENT COORDINATES OR DESTINATIONS.
   If the user does not supply coordinates or a known port (Goa, Mumbai, Cochin, Mangalore, Chennai), leave latitude and longitude null.
3. If essential origin coordinates are missing, add 'origin_coordinates' to missing_inputs, set clarification_needed to true, and provide a polite clarification_prompt.
4. If passage planning or route calculation is requested but destination coordinates are missing, add 'destination_coordinates' to missing_inputs, set clarification_needed to true, and provide a polite clarification_prompt.
5. Allowed objectives: 'general_maritime', 'fishing', 'passage_planning', 'safety_check', 'all'.
6. Allowed vessel types: 'small_craft', 'trawler', 'commercial_cargo', 'passenger'. Default is 'small_craft'.
Output MUST be a single valid JSON object."""


async def plan_mission_request(
    query: str | None,
    structured_params: dict[str, Any],
) -> tuple[StructuredPlanSchema, str]:
    """Execute LLM-based structured planning when available, falling back cleanly to deterministic planner.

    Returns:
        tuple of (StructuredPlanSchema, generation_mode) where mode is 'llm' or 'deterministic'.
    """
    # Fallback plan for baseline or failure cases
    fallback_plan = deterministic_plan_mission(query, structured_params)

    # If no natural language query was passed and structured params are already explicit, use deterministic plan
    if not query and structured_params.get("user_objective") in VALID_OBJECTIVES:
        return fallback_plan, "deterministic"

    user_text = query or str(structured_params.get("user_objective", ""))
    if not user_text.strip():
        return fallback_plan, "deterministic"

    user_prompt = (
        f"Request Text: \"{user_text}\"\n"
        f"Explicit Input Parameters: {structured_params}\n"
        f"Produce a JSON plan extracting user_objective, origin_latitude, origin_longitude, origin_name, "
        f"destination_latitude, destination_longitude, destination_name, forecast_time_window_hours, "
        f"vessel_type, target_species, planned_agents, missing_inputs, clarification_needed, clarification_prompt."
    )

    try:
        llm_dict, mode = await call_json_llm(
            system_prompt=PLANNING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            timeout=5.0,
        )
    except Exception:
        llm_dict, mode = None, "deterministic"

    if llm_dict and mode == "llm":
        try:
            # Validate through Pydantic schema
            plan = StructuredPlanSchema.model_validate(llm_dict)

            # Ensure coordinates from structured_params are preserved if model omitted them
            if plan.origin_latitude is None and structured_params.get("origin_latitude") is not None:
                plan.origin_latitude = structured_params.get("origin_latitude")
            if plan.origin_longitude is None and structured_params.get("origin_longitude") is not None:
                plan.origin_longitude = structured_params.get("origin_longitude")
            if plan.origin_latitude is None and structured_params.get("latitude") is not None:
                plan.origin_latitude = structured_params.get("latitude")
            if plan.origin_longitude is None and structured_params.get("longitude") is not None:
                plan.origin_longitude = structured_params.get("longitude")

            # Destination preservation
            if plan.destination_latitude is None and structured_params.get("destination_latitude") is not None:
                plan.destination_latitude = structured_params.get("destination_latitude")
            if plan.destination_longitude is None and structured_params.get("destination_longitude") is not None:
                plan.destination_longitude = structured_params.get("destination_longitude")

            # Ensure planned agents is non-empty
            if not plan.planned_agents:
                plan.planned_agents = fallback_plan.planned_agents

            # Safety check: if origin coordinates are completely missing, enforce clarification
            if plan.origin_latitude is None or plan.origin_longitude is None:
                if "origin_coordinates" not in plan.missing_inputs:
                    plan.missing_inputs.append("origin_coordinates")
                plan.clarification_needed = True
                if not plan.clarification_prompt:
                    plan.clarification_prompt = (
                        "Marine intelligence analysis requires geographical coordinates. "
                        "Please specify origin latitude and longitude (e.g. 15.0°N, 72.0°E) or a recognized port name."
                    )

            # Safety check: if route is planned in natural-language query but destination is missing, enforce clarification
            if query and (plan.user_objective == "passage_planning" or "route" in plan.planned_agents) and (
                plan.destination_latitude is None or plan.destination_longitude is None
            ):
                if "destination_coordinates" not in plan.missing_inputs:
                    plan.missing_inputs.append("destination_coordinates")
                plan.clarification_needed = True
                if not plan.clarification_prompt:
                    plan.clarification_prompt = (
                        "Passage planning requires a destination endpoint. "
                        "Please specify destination latitude and longitude or destination port name."
                    )

            return plan, "llm"
        except Exception:
            # Fall through cleanly to deterministic fallback
            pass

    return fallback_plan, "deterministic"
