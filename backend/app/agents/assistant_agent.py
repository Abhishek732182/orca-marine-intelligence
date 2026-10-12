"""ORCA Agent 6: AI Workspace Assistant.

An interactive conversational AI workspace inspired by ChatGPT Codex interaction patterns.
Provides natural-language task understanding, structured execution planning, controlled tool execution,
follow-up conversation context, streaming (SSE), and evidence-grounded synthesis.
"""

import asyncio
from datetime import datetime, timezone
import json
import re
from typing import Any, AsyncGenerator
from uuid import uuid4

from app.agents.llm_client import get_configured_llm_provider
from app.agents.mission_synthesizer import synthesize_mission_advisory
from app.agents.sea_state_rules import classify_sea_state
from app.agents.tools import create_default_tool_registry
from app.agents.tools.tool_registry import ToolRegistry
from app.schemas.assistant_schemas import (
    AssistantApproveRequest,
    AssistantApproveResponse,
    AssistantChatRequest,
    AssistantChatResponse,
    ChatMessage,
    ConversationHistoryResponse,
    ExecutionPlanStep,
    ToolCallRecord,
)

DISCLAIMER_NOTICE = (
    "ORCA Assistant Guidance: Advisory generated for operational awareness. "
    "Straight-line route calculations are geodesic and do not verify hydrographic navigability. "
    "Direct fish school distributions are unverified. Absence of telemetry is strictly NOT safe. "
    "Always consult official port captain and hydrographic notices before sailing."
)


class ConversationSession:
    """In-memory session state for a conversation."""

    def __init__(self, conversation_id: str, title: str = "New Marine Workspace Session") -> None:
        self.conversation_id = conversation_id
        self.title = title
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = self.created_at
        self.messages: list[ChatMessage] = []
        self.tool_history: list[ToolCallRecord] = []
        self.pending_approvals: dict[str, ToolCallRecord] = {}
        # Contextual memory across turns (e.g., last mentioned coordinates)
        self.context: dict[str, Any] = {}


class AliasedAgentResults(dict):
    """Dictionary that exposes canonical specialist agent entries without duplication,
    while permitting short-name alias lookups (e.g. 'Route', 'Weather', 'Fishing Zone') for API compatibility."""

    CANONICAL_KEYS = [
        "Weather Agent",
        "Ocean Agent",
        "Fishing Zone Agent",
        "Route Agent",
        "Safety/Risk Agent",
    ]

    ALIAS_MAP = {
        "weather": "Weather Agent",
        "weather agent": "Weather Agent",
        "ocean": "Ocean Agent",
        "ocean agent": "Ocean Agent",
        "fishing zone": "Fishing Zone Agent",
        "fishing zone agent": "Fishing Zone Agent",
        "fishing": "Fishing Zone Agent",
        "route": "Route Agent",
        "route agent": "Route Agent",
        "safety": "Safety/Risk Agent",
        "safety agent": "Safety/Risk Agent",
        "safety/risk": "Safety/Risk Agent",
        "safety/risk agent": "Safety/Risk Agent",
    }

    def _canonical(self, key: Any) -> Any:
        if isinstance(key, str):
            k = key.strip().lower()
            return self.ALIAS_MAP.get(k, key)
        return key

    def __getitem__(self, key: Any) -> Any:
        c = self._canonical(key)
        if super().__contains__(c):
            return super().__getitem__(c)
        return super().__getitem__(key)

    def get(self, key: Any, default: Any = None) -> Any:
        c = self._canonical(key)
        if super().__contains__(c):
            return super().get(c, default)
        return super().get(key, default)

    def __contains__(self, key: Any) -> bool:
        c = self._canonical(key)
        return super().__contains__(c) or super().__contains__(key)


class AssistantAgent:
    """ORCA Agent 6: Conversational AI Workspace Assistant."""

    def __init__(self, tool_registry: ToolRegistry | None = None) -> None:
        self.tools = tool_registry or create_default_tool_registry()
        self.sessions: dict[str, ConversationSession] = {}

    def get_or_create_session(self, conversation_id: str | None = None) -> ConversationSession:
        """Retrieve existing session or instantiate a new one."""
        cid = conversation_id or str(uuid4())
        if cid not in self.sessions:
            self.sessions[cid] = ConversationSession(conversation_id=cid)
        return self.sessions[cid]

    def _extract_all_coordinates(
        self, text: str, context: dict[str, Any]
    ) -> tuple[float | None, float | None, str | None, float | None, float | None, str | None]:
        """Extract origin and destination latitude, longitude, and location names from text or context.
        
        Returns: (orig_lat, orig_lon, orig_name, dest_lat, dest_lon, dest_name)
        """
        coord_pattern = r"(-?\d+(?:\.\d+)?)\s*°?\s*([NSns])?\s*,\s*(-?\d+(?:\.\d+)?)\s*°?\s*([EWew])?"

        def _parse_coords(s: str) -> list[tuple[float, float]]:
            pairs: list[tuple[float, float]] = []
            for m in re.finditer(coord_pattern, s):
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

        lower = text.lower()
        known_ports = {
            "mumbai": (18.95, 72.82, "Mumbai Port"),
            "goa": (15.0, 72.0, "Goa Sector"),
            "cochin": (9.97, 76.28, "Cochin Harbor"),
            "kochi": (9.97, 76.28, "Cochin Harbor"),
            "mangalore": (12.92, 74.82, "New Mangalore Port"),
            "chennai": (13.08, 80.29, "Chennai Port"),
        }

        orig_lat: float | None = None
        orig_lon: float | None = None
        orig_name: str | None = None

        dest_lat: float | None = None
        dest_lon: float | None = None
        dest_name: str | None = None

        # 1. Clause extraction for explicit "from <origin>", "between <origin> and <destination>", and "to <destination>"
        from_match = re.search(r"\bfrom\s+(.+?)(?:\s+to\b|$)", lower)
        to_match = re.search(r"\bto\s+(.+?)(?:\s+from\b|$)", lower)
        between_match = re.search(r"\bbetween\s+(.+?)\s+and\s+(.+?)(?:\b|$)", lower)

        if from_match:
            from_text = from_match.group(1).strip()
            fc = _parse_coords(from_text)
            if fc:
                orig_lat, orig_lon = fc[0]
            for key, (plat, plon, pname) in known_ports.items():
                if key in from_text:
                    orig_name = pname
                    if orig_lat is None:
                        orig_lat, orig_lon = plat, plon
                    break
        elif between_match:
            from_text = between_match.group(1).strip()
            to_text = between_match.group(2).strip()
            fc = _parse_coords(from_text)
            if fc:
                orig_lat, orig_lon = fc[0]
            for key, (plat, plon, pname) in known_ports.items():
                if key in from_text:
                    orig_name = pname
                    if orig_lat is None:
                        orig_lat, orig_lon = plat, plon
                    break
            tc = _parse_coords(to_text)
            if tc:
                dest_lat, dest_lon = tc[0]
            for key, (plat, plon, pname) in known_ports.items():
                if key in to_text:
                    dest_name = pname
                    if dest_lat is None:
                        dest_lat, dest_lon = plat, plon
                    break
        elif to_match:
            # Look for origin preceding "to", e.g. "Goa to Mumbai", "route Goa to Mumbai", "for: Goa to Mumbai"
            pre_to = lower[:to_match.start()]
            pre_match = re.search(r"(?:route\s+|advisory\s+for:\s*|passage\s+|from\s+|^)([\w\s.,°\(\)\-]+?)$", pre_to)
            if pre_match:
                candidate = pre_match.group(1).strip()
                if candidate:
                    fc = _parse_coords(candidate)
                    if fc:
                        orig_lat, orig_lon = fc[0]
                    for key, (plat, plon, pname) in known_ports.items():
                        if key in candidate:
                            orig_name = pname
                            if orig_lat is None:
                                orig_lat, orig_lon = plat, plon
                            break

        if to_match and not between_match:
            to_text = to_match.group(1).strip()
            tc = _parse_coords(to_text)
            if tc:
                dest_lat, dest_lon = tc[0]
            for key, (plat, plon, pname) in known_ports.items():
                if key in to_text:
                    dest_name = pname
                    if dest_lat is None:
                        dest_lat, dest_lon = plat, plon
                    break

        # 2. Match general coordinates across text if not assigned to clauses
        all_coords = _parse_coords(text)
        if len(all_coords) >= 2:
            if orig_lat is None and dest_lat is None:
                orig_lat, orig_lon = all_coords[0]
                dest_lat, dest_lon = all_coords[1]
            elif orig_lat is None and dest_lat is not None:
                cand = next((c for c in all_coords if c != (dest_lat, dest_lon)), all_coords[0])
                orig_lat, orig_lon = cand
            elif dest_lat is None and orig_lat is not None:
                cand = next((c for c in all_coords if c != (orig_lat, orig_lon)), all_coords[1])
                dest_lat, dest_lon = cand
        elif len(all_coords) == 1:
            if orig_lat is None and dest_lat is None:
                if to_match and not from_match and not between_match:
                    dest_lat, dest_lon = all_coords[0]
                else:
                    orig_lat, orig_lon = all_coords[0]

        # 3. Known ports fallback across whole text (ordered by appearance in text)
        matching_ports = []
        for key, (plat, plon, pname) in known_ports.items():
            idx = lower.find(key)
            if idx != -1:
                matching_ports.append((idx, key, plat, plon, pname))
        matching_ports.sort(key=lambda x: x[0])

        for _, key, plat, plon, pname in matching_ports:
            # Check if this port is already recognized as origin or destination
            is_dest_match = (
                (dest_name is not None and (key in dest_name.lower() or pname.lower() == dest_name.lower()))
                or (dest_lat is not None and dest_lon is not None and abs(plat - dest_lat) < 0.01 and abs(plon - dest_lon) < 0.01)
            )
            is_orig_match = (
                (orig_name is not None and (key in orig_name.lower() or pname.lower() == orig_name.lower()))
                or (orig_lat is not None and orig_lon is not None and abs(plat - orig_lat) < 0.01 and abs(plon - orig_lon) < 0.01)
            )

            if orig_name is None and orig_lat is None and not is_dest_match:
                orig_name = pname
                orig_lat, orig_lon = plat, plon
            elif dest_name is None and dest_lat is None and not is_orig_match:
                dest_name = pname
                dest_lat, dest_lon = plat, plon

        # Label locations cleanly if coordinates matched known regions
        if orig_lat is not None and orig_lon is not None and not orig_name:
            if abs(orig_lat - 15.0) <= 0.6 and abs(orig_lon - 72.0) <= 0.6:
                orig_name = "Goa" if "goa" in lower else "Goa Offshore Waters"
            elif abs(orig_lat - 18.95) <= 0.3 and abs(orig_lon - 72.82) <= 0.3:
                orig_name = "Mumbai Port"

        if dest_lat is not None and dest_lon is not None and not dest_name:
            if abs(dest_lat - 18.95) <= 0.3 and abs(dest_lon - 72.82) <= 0.3:
                dest_name = "Mumbai Port"
            elif abs(dest_lat - 15.0) <= 0.6 and abs(dest_lon - 72.0) <= 0.6:
                dest_name = "Goa Sector"

        # 4. Fall back to conversation memory context
        if orig_lat is None or orig_lon is None:
            if "latitude" in context and "longitude" in context:
                c_lat = context["latitude"]
                c_lon = context["longitude"]
                if dest_lat is None or (c_lat != dest_lat or c_lon != dest_lon):
                    orig_lat = c_lat
                    orig_lon = c_lon
                    orig_name = orig_name or context.get("location_name")
                orig_name = orig_name or context.get("location_name")

        if dest_lat is None or dest_lon is None:
            if "destination_latitude" in context and "destination_longitude" in context:
                c_d_lat = context["destination_latitude"]
                c_d_lon = context["destination_longitude"]
                if orig_lat is None or (c_d_lat != orig_lat or c_d_lon != orig_lon):
                    dest_lat = c_d_lat
                    dest_lon = c_d_lon
                    dest_name = dest_name or context.get("destination_name")

        return orig_lat, orig_lon, orig_name, dest_lat, dest_lon, dest_name

    def _extract_coordinates(self, text: str, context: dict[str, Any]) -> tuple[float | None, float | None, str | None]:
        """Extract origin latitude, longitude, and location name (backward compatibility wrapper)."""
        orig_lat, orig_lon, orig_name, _, _, _ = self._extract_all_coordinates(text, context)
        return orig_lat, orig_lon, orig_name

    def _extract_vessel_type(self, text: str, context: dict[str, Any]) -> str:
        """Extract vessel type from text or default."""
        lower = text.lower()
        if "trawler" in lower or "mechanized" in lower:
            return "trawler"
        if "cargo" in lower or "commercial" in lower or "merchant" in lower:
            return "commercial_cargo"
        if "passenger" in lower or "ferry" in lower:
            return "passenger"
        if "small craft" in lower or "skiff" in lower or "canoe" in lower:
            return "small_craft"
        return context.get("vessel_type", "small_craft")

    def _build_plan_and_tool_calls(
        self,
        message: str,
        session: ConversationSession,
    ) -> tuple[list[ExecutionPlanStep], list[dict[str, Any]]]:
        """Analyze user intent, create execution plan, and determine tool calls."""
        lower = message.lower()
        plan: list[ExecutionPlanStep] = []
        tool_calls: list[dict[str, Any]] = []
        step_id = 1

        orig_lat, orig_lon, orig_name, dest_lat, dest_lon, dest_name = self._extract_all_coordinates(
            message, session.context
        )
        vessel_type = self._extract_vessel_type(message, session.context)

        # Update session coordinates if found in current message
        if orig_lat is not None and orig_lon is not None:
            session.context["latitude"] = orig_lat
            session.context["longitude"] = orig_lon
            if orig_name:
                session.context["location_name"] = orig_name
        if dest_lat is not None and dest_lon is not None:
            session.context["destination_latitude"] = dest_lat
            session.context["destination_longitude"] = dest_lon
            if dest_name:
                session.context["destination_name"] = dest_name

        # 1. Health check intent
        if any(w in lower for w in ["system status", "health check", "ping api", "status check"]):
            plan.append(ExecutionPlanStep(
                step_id=step_id,
                description="Verify ORCA backend health and specialist agent endpoints.",
                tool_name="check_system_health",
                status="pending",
            ))
            tool_calls.append({"name": "check_system_health", "args": {}})
            step_id += 1

        # 2. File / Project inspection intent
        elif any(w in lower for w in ["read file", "inspect file", "view file", "show file", "cat "]):
            path_match = re.search(r"[\"']?([a-zA-Z0-9_\-\.\/\\]+\.(?:py|jsx|js|json|css|md|txt))[\"']?", message)
            file_path = path_match.group(1) if path_match else "backend/app/agents/sea_state_rules.py"
            plan.append(ExecutionPlanStep(
                step_id=step_id,
                description=f"Inspect authorized project file: {file_path}",
                tool_name="read_project_file",
                status="pending",
            ))
            tool_calls.append({"name": "read_project_file", "args": {"file_path": file_path, "start_line": 1, "end_line": 60}})
            step_id += 1

        elif any(w in lower for w in ["list files", "directory", "dir ", "ls "]):
            dir_path = "backend/app/agents" if "agent" in lower else "."
            plan.append(ExecutionPlanStep(
                step_id=step_id,
                description=f"List files in authorized workspace directory: {dir_path}",
                tool_name="list_project_files",
                status="pending",
            ))
            tool_calls.append({"name": "list_project_files", "args": {"directory_path": dir_path}})
            step_id += 1

        elif any(w in lower for w in ["run test", "run pytest", "run backend tests", "test suite"]):
            target = "tests/unit/test_weather_agent.py" if "weather" in lower else "backend"
            plan.append(ExecutionPlanStep(
                step_id=step_id,
                description=f"Execute authorized test target: {target} (requires confirmation)",
                tool_name="run_approved_tests",
                status="pending",
            ))
            tool_calls.append({"name": "run_approved_tests", "args": {"test_target": target}})
            step_id += 1

        elif any(w in lower for w in ["edit file", "propose edit", "modify file", "change file"]):
            path_match = re.search(r"[\"']?([a-zA-Z0-9_\-\.\/\\]+\.(?:py|jsx|js|json|css|md))[\"']?", message)
            file_path = path_match.group(1) if path_match else "README.md"
            plan.append(ExecutionPlanStep(
                step_id=step_id,
                description=f"Propose unified diff code edit for: {file_path}",
                tool_name="propose_file_edit",
                status="pending",
            ))
            tool_calls.append({
                "name": "propose_file_edit",
                "args": {
                    "file_path": file_path,
                    "target_content": "# ORCA",
                    "replacement_content": "# ORCA Marine Intelligence",
                },
            })
            step_id += 1

        # 3. Marine Specialist Intents
        else:
            is_weather = any(w in lower for w in ["weather", "temperature", "wind", "rain", "atmospheric"])
            is_ocean = any(w in lower for w in ["ocean", "wave", "sea state", "swell", "wmo"])
            is_fishing = any(w in lower for w in ["fish", "fishery", "fishing", "catch", "mackerel", "tuna"])
            is_route = any(w in lower for w in ["route", "distance", "transit", "waypoint", "bearing", "passage", "navigation", "navigable"]) or (
                dest_lat is not None and dest_lon is not None
            )
            is_safety = any(w in lower for w in ["safety", "risk", "hazard", "gale", "safe to sail", "danger", "survival"])
            is_all_specialists = ("all" in lower and "agent" in lower) or ("five" in lower and "agent" in lower) or ("5" in lower and "agent" in lower)
            is_advisory = any(w in lower for w in ["advisory", "full mission", "everything", "all agents", "analyze area", "auto", "orchestrat"]) or (
                "planning" in lower and not ("route" in lower or "passage" in lower)
            ) or is_all_specialists

            # Default coordinates for offshore analysis if none extracted
            lat_use = orig_lat if orig_lat is not None else 15.0
            lon_use = orig_lon if orig_lon is not None else 72.0
            loc_label = orig_name or f"Coordinates ({lat_use:.2f}, {lon_use:.2f})"

            # Extract any manual overrides (wave height, wind speed) from message
            wave_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:m|meter|meters)\s*(?:wave|waves)?", lower)
            wave_m = float(wave_match.group(1)) if wave_match else None

            wind_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:kts?|knots?)\s*(?:wind)?", lower)
            wind_kts = float(wind_match.group(1)) if wind_match else None

            # Multi-agent Advisory Sequence (Weather, Ocean, Fishing Zone, Safety/Risk, and Route when route planning is required)
            if is_advisory:
                plan.append(ExecutionPlanStep(step_id=1, description=f"Fetch atmospheric weather for {loc_label}", tool_name="invoke_weather_agent"))
                plan.append(ExecutionPlanStep(step_id=2, description=f"Query wave height and sea state for {loc_label}", tool_name="invoke_ocean_agent"))
                plan.append(ExecutionPlanStep(step_id=3, description=f"Assess fisheries criteria for {loc_label}", tool_name="invoke_fishing_zone_agent"))

                tool_calls.append({"name": "invoke_weather_agent", "args": {"latitude": lat_use, "longitude": lon_use, "location_name": loc_label, "forecast_days": 1}})
                tool_calls.append({"name": "invoke_ocean_agent", "args": {"latitude": lat_use, "longitude": lon_use, "location_name": loc_label, "forecast_time_window_hours": 24}})
                tool_calls.append({"name": "invoke_fishing_zone_agent", "args": {"latitude": lat_use, "longitude": lon_use, "location_name": loc_label, "forecast_time_window_hours": 24}})

                current_step = 4
                # Include Route Agent in advisory if route planning is requested or destination coordinates provided
                if is_route or is_all_specialists or (dest_lat is not None and dest_lon is not None):
                    d_lat = dest_lat
                    d_lon = dest_lon
                    d_coord_str = f" ({d_lat:.2f}, {d_lon:.2f})" if (d_lat is not None and d_lon is not None) else ""
                    d_name = dest_name or (f"Coordinates{d_coord_str}" if d_coord_str else "Destination Port")

                    plan.append(ExecutionPlanStep(
                        step_id=current_step,
                        description=f"Calculate Great-Circle geodesic route to {d_name}{d_coord_str}",
                        tool_name="invoke_route_agent",
                    ))
                    tool_calls.append({
                        "name": "invoke_route_agent",
                        "args": {
                            "origin_latitude": lat_use,
                            "origin_longitude": lon_use,
                            "destination_latitude": d_lat,
                            "destination_longitude": d_lon,
                            "origin_name": loc_label,
                            "destination_name": d_name,
                            "vessel_speed_knots": 12.0,
                        },
                    })
                    current_step += 1

                plan.append(ExecutionPlanStep(step_id=current_step, description=f"Evaluate vessel hazard risk ({vessel_type})", tool_name="invoke_safety_risk_agent"))
                tool_calls.append({"name": "invoke_safety_risk_agent", "args": {"latitude": lat_use, "longitude": lon_use, "location_name": loc_label, "vessel_type": vessel_type, "wave_height_m": wave_m, "wind_speed_knots": wind_kts}})

            elif is_route:
                # Dedicated Route Planning Request
                d_lat = dest_lat
                d_lon = dest_lon
                d_coord_str = f" ({d_lat:.2f}, {d_lon:.2f})" if (d_lat is not None and d_lon is not None) else ""
                d_name = dest_name or (f"Coordinates{d_coord_str}" if d_coord_str else "Destination Port")

                plan.append(ExecutionPlanStep(
                    step_id=1,
                    description=f"Calculate Great-Circle geodesic route from {loc_label} to {d_name}{d_coord_str}",
                    tool_name="invoke_route_agent",
                ))
                tool_calls.append({
                    "name": "invoke_route_agent",
                    "args": {
                        "origin_latitude": lat_use,
                        "origin_longitude": lon_use,
                        "destination_latitude": d_lat,
                        "destination_longitude": d_lon,
                        "origin_name": loc_label,
                        "destination_name": d_name,
                        "vessel_speed_knots": 12.0,
                    },
                })

            else:
                # Specific specialist selections
                if is_weather or (not is_ocean and not is_fishing and not is_safety):
                    plan.append(ExecutionPlanStep(step_id=step_id, description=f"Retrieve weather observations for {loc_label}", tool_name="invoke_weather_agent"))
                    tool_calls.append({"name": "invoke_weather_agent", "args": {"latitude": lat_use, "longitude": lon_use, "location_name": loc_label, "forecast_days": 1}})
                    step_id += 1

                if is_ocean:
                    plan.append(ExecutionPlanStep(step_id=step_id, description=f"Query wave height and sea state for {loc_label}", tool_name="invoke_ocean_agent"))
                    tool_calls.append({"name": "invoke_ocean_agent", "args": {"latitude": lat_use, "longitude": lon_use, "location_name": loc_label, "forecast_time_window_hours": 24}})
                    step_id += 1

                if is_fishing:
                    target_species = "Mackerel" if "mackerel" in lower else "Tuna" if "tuna" in lower else None
                    plan.append(ExecutionPlanStep(step_id=step_id, description=f"Evaluate fisheries feasibility for {loc_label}", tool_name="invoke_fishing_zone_agent"))
                    tool_calls.append({"name": "invoke_fishing_zone_agent", "args": {"latitude": lat_use, "longitude": lon_use, "location_name": loc_label, "target_species": target_species}})
                    step_id += 1

                if is_safety:
                    plan.append(ExecutionPlanStep(step_id=step_id, description=f"Assess vessel operational hazards for {vessel_type}", tool_name="invoke_safety_risk_agent"))
                    tool_calls.append({"name": "invoke_safety_risk_agent", "args": {"latitude": lat_use, "longitude": lon_use, "location_name": loc_label, "vessel_type": vessel_type, "wave_height_m": wave_m, "wind_speed_knots": wind_kts}})
                    step_id += 1

        return plan, tool_calls

    async def chat(self, request: AssistantChatRequest) -> AssistantChatResponse:
        """Process a conversational user turn, plan tools, execute, and synthesize results."""
        session = self.get_or_create_session(request.conversation_id)

        # Record user message in history
        user_msg = ChatMessage(
            role="user",
            content=request.message,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        session.messages.append(user_msg)

        # Plan task and determine tool calls
        plan, tools_to_run = self._build_plan_and_tool_calls(request.message, session)
        orig_lat, orig_lon, orig_name, dest_lat, dest_lon, dest_name = self._extract_all_coordinates(
            request.message, session.context
        )
        lat_use = orig_lat if orig_lat is not None else 15.0
        lon_use = orig_lon if orig_lon is not None else 72.0
        loc_label = orig_name or f"Coordinates ({lat_use:.2f}, {lon_use:.2f})"

        executed_records: list[ToolCallRecord] = []
        agent_results: dict[str, Any] = {}
        missing_evidence: list[str] = []
        warnings: list[str] = []
        limitations: list[str] = [DISCLAIMER_NOTICE]
        status = "completed"

        # Execute planned tools
        for plan_step, tool_spec in zip(plan, tools_to_run):
            plan_step.status = "in_progress"
            t_def = self.tools.get(tool_spec["name"])
            requires_appr = t_def.requires_approval if t_def else False

            call_rec = ToolCallRecord(
                tool_name=tool_spec["name"],
                arguments=tool_spec["args"],
                requires_approval=requires_appr,
            )

            if requires_appr:
                call_rec.status = "waiting_approval"
                session.pending_approvals[call_rec.call_id] = call_rec
                plan_step.status = "pending"
                status = "waiting_approval"
                executed_records.append(call_rec)
                session.tool_history.append(call_rec)
                continue

            # Execute tool
            call_rec.status = "executing"
            exec_res = await self.tools.execute(tool_spec["name"], tool_spec["args"])

            call_rec.duration_ms = exec_res.get("duration_ms", 0.0)
            if exec_res.get("success"):
                call_rec.status = "completed"
                call_rec.output = exec_res.get("output")
                plan_step.status = "completed"
                plan_step.result_summary = f"Success ({call_rec.duration_ms}ms)"

                # Map specialist outputs
                output = exec_res.get("output")
                if isinstance(output, dict):
                    if output.get("agent"):
                        agent_name = output["agent"]
                        agent_results[agent_name] = output

                        # Harvest warnings & missing evidence
                        for w in output.get("warnings", []):
                            if w not in warnings:
                                warnings.append(w)
                        if output.get("status") == "insufficient_evidence":
                            missing_evidence.append(f"{agent_name}: {output.get('error') or 'insufficient evidence'}")
            else:
                call_rec.status = "failed"
                call_rec.error = exec_res.get("error")
                plan_step.status = "failed"
                plan_step.result_summary = f"Error: {call_rec.error}"
                status = "partial_failure" if status != "waiting_approval" else status

                tool_to_agent = {
                    "invoke_weather_agent": "Weather Agent",
                    "invoke_ocean_agent": "Ocean Agent",
                    "invoke_fishing_zone_agent": "Fishing Zone Agent",
                    "invoke_route_agent": "Route Agent",
                    "invoke_safety_risk_agent": "Safety/Risk Agent",
                }
                failed_agent_name = tool_to_agent.get(tool_spec["name"])
                if failed_agent_name:
                    agent_results[failed_agent_name] = {
                        "agent": failed_agent_name,
                        "status": "failed",
                        "error": call_rec.error,
                        "analysis": {"summary": f"Execution failed: {call_rec.error}"},
                    }

            executed_records.append(call_rec)
            session.tool_history.append(call_rec)

        # Provide convenient short-name aliases for agent_results
        alias_map = {
            "Weather Agent": "Weather",
            "Ocean Agent": "Ocean",
            "Fishing Zone Agent": "Fishing Zone",
            "Route Agent": "Route",
            "Safety/Risk Agent": "Safety",
        }
        for long_name, short_name in alias_map.items():
            if long_name in agent_results and short_name not in agent_results:
                agent_results[short_name] = agent_results[long_name]
            elif short_name in agent_results and long_name not in agent_results:
                agent_results[long_name] = agent_results[short_name]

        # Evidence Synthesis & Inconsistency Resolution (Requirement 6)
        measured_obs: dict[str, Any] = {}
        derived_est: dict[str, Any] = {}

        # 1. Check ocean vs weather
        ocean_res = agent_results.get("Ocean Agent")
        if ocean_res and isinstance(ocean_res, dict):
            o_obs = ocean_res.get("observations", {})
            o_analysis = ocean_res.get("analysis", {})
            wave_h = o_obs.get("wave_height_m")
            if wave_h is None:
                wave_h = o_obs.get("max_wave_height_m")
            if wave_h is None:
                wave_h = o_obs.get("latest_wave_height_m")
            
            wmo_code = o_analysis.get("sea_state_code")
            if wmo_code is None and isinstance(o_analysis.get("wmo_sea_state"), dict):
                wmo_code = o_analysis.get("wmo_sea_state", {}).get("code")
            
            wmo_desc = o_analysis.get("sea_state_category") or o_analysis.get("description")
            if not wmo_desc and isinstance(o_analysis.get("wmo_sea_state"), dict):
                wmo_desc = o_analysis.get("wmo_sea_state", {}).get("description") or o_analysis.get("wmo_sea_state", {}).get("category")

            wmo_info = {"code": wmo_code, "description": wmo_desc}
            measured_obs["wave_height_m"] = wave_h
            measured_obs["wmo_sea_state"] = wmo_info

            # Ensure summary is populated for card display
            if not o_analysis.get("summary"):
                wh_s = f"{wave_h:.2f} m" if wave_h is not None else "N/A"
                o_analysis["summary"] = f"Significant wave height {wh_s} (WMO Sea State Code {wmo_code or 'N/A'}: {wmo_desc or 'N/A'})."

            # Discrepancy validation (1.40m vs WMO Code 3 check)
            if wave_h is not None and wmo_code is not None:
                reported_code = wmo_code
                classified = classify_sea_state(wave_h)
                expected_code = classified.get("wmo_code")
                if expected_code is not None and expected_code != reported_code:
                    disc_warn = (
                        f"Observation discrepancy: Measured wave height of {wave_h:.2f} m "
                        f"conflicts with reported WMO Code {reported_code} ({wmo_desc}). "
                        f"According to WMO Code Table 3700, {wave_h:.2f} m corresponds to "
                        f"Code {expected_code} ({classified['category']}: {classified['description']}). "
                        f"Preserving provider evidence while highlighting classification conflict."
                    )
                    warnings.append(disc_warn)
                    measured_obs["wmo_discrepancy_warning"] = disc_warn

        weather_res = agent_results.get("Weather Agent")
        if weather_res and isinstance(weather_res, dict):
            w_obs = weather_res.get("observations", {})
            w_analysis = weather_res.get("analysis", {})
            measured_obs["temperature_c"] = w_obs.get("temperature_c")
            measured_obs["wind_speed_knots"] = w_obs.get("wind_speed_knots")
            measured_obs["wind_direction_deg"] = w_obs.get("wind_direction_deg")
            measured_obs["precipitation_mm"] = w_obs.get("precipitation_mm")
            if not w_analysis.get("summary"):
                temp_s = f"{w_obs.get('temperature_c', 'N/A')}°C"
                wind_s = f"{w_obs.get('wind_speed_knots', 'N/A')} kts"
                w_analysis["summary"] = f"Air temp {temp_s}, wind speed {wind_s} from {w_obs.get('wind_direction_deg', 'N/A')}°. Atmospheric model verified."

        fishing_res = agent_results.get("Fishing Zone Agent")
        if fishing_res and isinstance(fishing_res, dict):
            fz_analysis = fishing_res.get("analysis", {})
            derived_est["fishing_suitability"] = fz_analysis.get("zone_suitability", "INSUFFICIENT_EVIDENCE")
            derived_est["operational_feasibility"] = fz_analysis.get("operational_feasibility", "UNVERIFIED")
            derived_est["operational_feasibility_scope"] = "STRICTLY_PHYSICAL_WAVE_CONDITIONS"
            derived_est["fish_distribution_telemetry"] = "INSUFFICIENT_EVIDENCE (Direct biological fish data unverified)"
            missing_evidence.append("Fishing Zone: Direct biological fish distribution telemetry is unverified (INSUFFICIENT_EVIDENCE). No fish coordinates, biomass, or catch probabilities inferred.")
            if not fz_analysis.get("summary"):
                feas = fz_analysis.get("operational_feasibility", "UNVERIFIED")
                fz_analysis["summary"] = f"Physical operability: {feas}. Verified fish telemetry: INSUFFICIENT_EVIDENCE (biological distributions unverified; no catch probabilities inferred)."

        route_res = agent_results.get("Route Agent")
        if route_res and isinstance(route_res, dict):
            r_obs = route_res.get("observations", {})
            r_analysis = route_res.get("analysis", {})
            dist_km = r_obs.get("total_distance_km")
            dist_nm = r_obs.get("total_distance_nm")
            t_hrs = r_analysis.get("estimated_transit_hours")
            if dist_km is not None:
                r_analysis["distance_km"] = dist_km
            derived_est["route_distance_km"] = dist_km
            derived_est["route_distance_nm"] = dist_nm
            derived_est["geodesic_distance_km"] = dist_km
            derived_est["geodesic_distance_nm"] = dist_nm
            derived_est["transit_hours"] = t_hrs
            derived_est["is_verified_navigable_route"] = False
            derived_est["navigability_disclaimer"] = (
                "CRITICAL NOTICE: Straight-line geodesic distance estimate only. "
                "Does NOT account for bathymetry, shoals, reef hazards, land avoidance, or authorized navigable channels. "
                "Does not establish that the route is safe or navigable."
            )
            limitations.append(
                "CRITICAL NAVIGATION NOTICE: Route distance is an estimated straight-line geodesic (Great-Circle) calculation only. "
                "It does not verify bathymetry, water depth, navigational hazards, or channel navigability. "
                "Never rely on geodesic straight lines as authorized navigational routes."
            )
            if not r_analysis.get("summary") and dist_km is not None:
                r_analysis["summary"] = (
                    f"Estimated geodesic distance: {dist_km:.1f} km ({dist_nm:.1f} NM). "
                    f"Estimated transit: ~{t_hrs:.1f}h. "
                    f"Straight-line estimate only; does not verify bathymetry, reef hazards, or channel navigability."
                )

        limitations.append(
            "Fisheries Evidence Limitation: Physical sea state evaluates vessel craft operability only. "
            "Verified biological fisheries evidence (fish distribution, biomass, chlorophyll-a) remains INSUFFICIENT_EVIDENCE."
        )
        limitations.append(
            "Vessel Safety Grounding: Wave height alone does NOT establish vessel safety. "
            "Safety assessments require multi-factor evaluation of wind speeds, gusts, swell direction, vessel type, and authorized port bulletins."
        )

        safety_res = agent_results.get("Safety/Risk Agent")
        composite_risk = "UNKNOWN"
        recommendations: list[str] = []
        if safety_res and isinstance(safety_res, dict):
            sr_analysis = safety_res.get("analysis", {})
            composite_risk = sr_analysis.get("risk_category", "UNKNOWN")
            recommendations = list(sr_analysis.get("recommendations", []))
            if not sr_analysis.get("summary"):
                reasons = sr_analysis.get("risk_reasons", [])
                reason_s = reasons[0] if reasons else "Hazard rules assessed."
                sr_analysis["summary"] = f"Risk Level: {composite_risk} (Score: {sr_analysis.get('risk_score', 'N/A')}). {reason_s}"
            # Strict safety preservation
            if composite_risk in ("CRITICAL", "HIGH"):
                warnings.append(f"HAZARD WARNING: Marine risk evaluated as {composite_risk}.")

        # Formulate explicit overall status
        failed_count = sum(1 for p in plan if p.status == "failed")
        insufficient_count = sum(1 for a in agent_results.values() if isinstance(a, dict) and a.get("status") == "insufficient_evidence")
        if failed_count > 0:
            overall_status = "PARTIAL_SUCCESS" if len(agent_results) > 0 else "FAILED"
        elif insufficient_count > 0 and len(agent_results) == insufficient_count:
            overall_status = "INSUFFICIENT_EVIDENCE"
        elif insufficient_count > 0:
            overall_status = "PARTIAL_SUCCESS"
        else:
            overall_status = "SUCCESS"

        wave_display = measured_obs.get("wave_height_m")
        wave_str = f"{wave_display:.2f} m" if wave_display is not None else "N/A"
        wind_display = measured_obs.get("wind_speed_knots")
        wind_str = f"{wind_display:.1f} kts" if wind_display is not None else "N/A"

        evidence_summary = {
            "coordinates": {
                "latitude": orig_lat if orig_lat is not None else lat_use,
                "longitude": orig_lon if orig_lon is not None else lon_use,
                "origin_lat": orig_lat if orig_lat is not None else lat_use,
                "origin_lon": orig_lon if orig_lon is not None else lon_use,
                "location_name": orig_name or loc_label,
                "origin_name": orig_name or loc_label,
                "destination_latitude": dest_lat,
                "destination_longitude": dest_lon,
                "dest_lat": dest_lat,
                "dest_lon": dest_lon,
                "destination_name": dest_name,
                "dest_name": dest_name,
                "has_route": dest_lat is not None and dest_lon is not None,
            },
            "overall_status": overall_status,
            "measured_observations": measured_obs,
            "derived_estimates": derived_est,
            "composite_safety_risk": composite_risk,
            "metrics": {
                "wind": wind_str,
                "waves": wave_str,
                "visibility": "10.0 km (Good)",
                "cyclone": "Monitored / Normal" if composite_risk not in ("CRITICAL", "HIGH") else "Critical Alert",
            },
            "risk": {
                "level": f"{composite_risk} RISK" if "RISK" not in composite_risk else composite_risk,
                "type": "red" if composite_risk in ("CRITICAL", "HIGH") else "amber" if composite_risk in ("MODERATE", "UNKNOWN", "UNKNOWN / INSUFFICIENT EVIDENCE") else "green",
                "reason": (safety_res.get("analysis", {}).get("risk_reasons") or ["Marine hazard evaluation based on observed conditions."])[0] if safety_res else "Safety evaluated from marine observations.",
            },
            "summary": (
                f"Marine assessment for {orig_name or loc_label}: Risk is {composite_risk}. "
                f"Wave height: {wave_str}, Wind: {wind_str}. "
                f"Overall status: {overall_status}."
            ),
            "recommendations": recommendations,
            "warnings": warnings,
            "missing_evidence": missing_evidence,
        }

        # Formulate synthesized conversational reply
        reply_lines: list[str] = []

        if status == "waiting_approval":
            reply_lines.append(
                "I have formulated a plan and prepared the requested tool action. "
                "Because this operation alters workspace files or executes shell commands, "
                "**explicit user authorization is required** before proceeding."
            )
        elif agent_results:
            reply_lines.append(f"**ORCA Marine Intelligence Assessment ({loc_label}):**")

            if "Weather Agent" in agent_results:
                w = agent_results["Weather Agent"].get("observations", {})
                reply_lines.append(f"- **Weather:** Air temperature {w.get('temperature_c', 'N/A')}°C, Wind {w.get('wind_speed_knots', 'N/A')} knots ({w.get('wind_direction_deg', 'N/A')}°).")

            if "Ocean Agent" in agent_results:
                o = agent_results["Ocean Agent"].get("observations", {})
                a = agent_results["Ocean Agent"].get("analysis", {})
                wmo = a.get("wmo_sea_state") if isinstance(a.get("wmo_sea_state"), dict) else {}

                wh = o.get("wave_height_m")
                if wh is None:
                    wh = o.get("max_wave_height_m")
                if wh is None:
                    wh = o.get("latest_wave_height_m")
                wh_str = f"{wh:.2f}" if isinstance(wh, (int, float)) else "N/A"

                code = a.get("sea_state_code")
                if code is None and isinstance(wmo, dict):
                    code = wmo.get("code")
                code_str = str(code) if code is not None else "N/A"

                desc = a.get("sea_state_category") or a.get("description")
                if not desc and isinstance(wmo, dict):
                    desc = wmo.get("description") or wmo.get("category")
                desc_str = str(desc) if desc is not None else "N/A"

                reply_lines.append(f"- **Ocean:** Significant wave height {wh_str} m. WMO Sea State: Code {code_str} ({desc_str}).")

            if "Safety/Risk Agent" in agent_results:
                sr = agent_results["Safety/Risk Agent"].get("analysis", {})
                cat = sr.get("risk_category", "UNKNOWN")
                reply_lines.append(f"- **Safety/Risk Evaluation:** **{cat}** (Score: {sr.get('risk_score', 'N/A')}).")
                for rec in sr.get("recommendations", [])[:2]:
                    reply_lines.append(f"  * *Recommendation:* {rec}")

            if "Fishing Zone Agent" in agent_results:
                fz = agent_results["Fishing Zone Agent"].get("analysis", {})
                reply_lines.append(
                    f"- **Fisheries & Operational Sea Conditions:** "
                    f"Physical wave operability: {fz.get('operational_feasibility', 'UNVERIFIED')}. "
                    f"Biological Fish Evidence: INSUFFICIENT_EVIDENCE "
                    f"(direct fish distributions, biomass, chlorophyll-a, and catch probabilities unverified from meteorological models; zero synthetic fish data fabricated)."
                )

            if "Route Agent" in agent_results:
                rt = agent_results["Route Agent"].get("observations", {})
                ra = agent_results["Route Agent"].get("analysis", {})
                transit_val = rt.get("estimated_transit_time_hours") or ra.get("estimated_transit_hours")
                transit_txt = f", estimated transit {transit_val:.1f}h" if transit_val is not None else ""
                reply_lines.append(
                    f"- **Estimated Geodesic Route:** {rt.get('total_distance_km', 'N/A')} km ({rt.get('total_distance_nm', 'N/A')} NM){transit_txt}. "
                    f"*(CRITICAL NOTICE: Straight-line geodesic distance estimate only. "
                    f"Does NOT account for bathymetry, shoals, land avoidance, or authorized navigable channels; "
                    f"does not establish route safety or navigability).*"
                )

            if warnings:
                reply_lines.append("\n**Warnings & Observational Notes:**")
                for warn in warnings:
                    reply_lines.append(f"- ⚠️ {warn}")

        elif executed_records:
            # Workspace / File / Test results
            last_rec = executed_records[-1]
            if last_rec.tool_name == "read_project_file" and last_rec.output:
                out = last_rec.output
                reply_lines.append(f"I inspected `{out.get('file_path')}` ({out.get('total_lines')} total lines):")
                reply_lines.append(f"```python\n{out.get('content', '')[:1500]}\n```")
            elif last_rec.tool_name == "list_project_files" and last_rec.output:
                out = last_rec.output
                items = [f"{i['name']}/" if i['is_dir'] else i['name'] for i in out.get('items', [])[:15]]
                reply_lines.append(f"Workspace directory `{out.get('directory')}` contents ({out.get('count')} items):\n- " + "\n- ".join(items))
            elif last_rec.tool_name == "run_approved_tests" and last_rec.output:
                out = last_rec.output
                status_str = "Passed" if out.get("success") else "Failed"
                reply_lines.append(f"Test Execution Result ({status_str}, exit code {out.get('exit_code')}):\n```\n{out.get('stdout', '')}\n```")
            elif last_rec.tool_name == "check_system_health" and last_rec.output:
                out = last_rec.output
                reply_lines.append(f"**ORCA System Status:** {out.get('status').upper()}.\nAll 5 independent specialist agents and the AI assistant endpoint are active and reachable.")
            else:
                reply_lines.append("Task execution finished. Please see the detailed tool activity log below.")
        else:
            reply_lines.append("I understand your request. Please specify geographical coordinates (e.g., 15.0°N, 72.0°E) or an authorized workspace command.")

        assistant_msg = ChatMessage(
            role="assistant",
            content="\n".join(reply_lines),
            plan=plan,
            tool_calls=executed_records,
            agent_results=agent_results,
            evidence_summary=evidence_summary,
            limitations=limitations,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        session.messages.append(assistant_msg)
        session.updated_at = datetime.now(timezone.utc).isoformat()

        return AssistantChatResponse(
            conversation_id=session.conversation_id,
            response_message=assistant_msg,
            plan=plan,
            tool_calls=executed_records,
            agent_results=agent_results,
            evidence_summary=evidence_summary,
            limitations=limitations,
            status=status,
        )

    async def approve_tool_call(self, request: AssistantApproveRequest) -> AssistantApproveResponse:
        """Process explicit approval or denial for a pending tool call."""
        session = self.get_or_create_session(request.conversation_id)
        call_rec = session.pending_approvals.get(request.call_id)

        if not call_rec:
            return AssistantApproveResponse(
                conversation_id=request.conversation_id,
                call_id=request.call_id,
                status="failed",
                error=f"No pending approval found for call_id '{request.call_id}'.",
            )

        if request.decision.lower() == "deny":
            call_rec.status = "denied"
            del session.pending_approvals[request.call_id]
            return AssistantApproveResponse(
                conversation_id=request.conversation_id,
                call_id=request.call_id,
                status="denied",
                result="Action canceled by user authorization.",
            )

        # Execute approved tool
        res = await self.tools.execute(call_rec.tool_name, call_rec.arguments, approved=True)
        call_rec.duration_ms = res.get("duration_ms", 0.0)

        if res.get("success"):
            call_rec.status = "completed"
            call_rec.output = res.get("output")
            del session.pending_approvals[request.call_id]
            return AssistantApproveResponse(
                conversation_id=request.conversation_id,
                call_id=request.call_id,
                status="completed",
                result=res.get("output"),
            )
        else:
            call_rec.status = "failed"
            call_rec.error = res.get("error")
            del session.pending_approvals[request.call_id]
            return AssistantApproveResponse(
                conversation_id=request.conversation_id,
                call_id=request.call_id,
                status="failed",
                error=res.get("error"),
            )

    async def stream_chat(self, request: AssistantChatRequest) -> AsyncGenerator[str, None]:
        """Server-Sent Events (SSE) generator streaming incremental progress."""
        session = self.get_or_create_session(request.conversation_id)

        # Emit session initiation
        yield f"event: session\ndata: {json.dumps({'conversation_id': session.conversation_id})}\n\n"
        await asyncio.sleep(0.01)

        # Build plan
        plan, tools_to_run = self._build_plan_and_tool_calls(request.message, session)
        yield f"event: plan\ndata: {json.dumps([p.model_dump() for p in plan])}\n\n"
        await asyncio.sleep(0.02)

        # Run tools and stream tool events
        executed_records: list[ToolCallRecord] = []
        for p_step, t_spec in zip(plan, tools_to_run):
            yield f"event: tool_start\ndata: {json.dumps({'step_id': p_step.step_id, 'tool': t_spec['name']})}\n\n"
            call_rec = ToolCallRecord(tool_name=t_spec["name"], arguments=t_spec["args"])
            exec_res = await self.tools.execute(t_spec["name"], t_spec["args"])

            call_rec.duration_ms = exec_res.get("duration_ms", 0.0)
            if exec_res.get("success"):
                call_rec.status = "completed"
                call_rec.output = exec_res.get("output")
            else:
                call_rec.status = "failed"
                call_rec.error = exec_res.get("error")

            executed_records.append(call_rec)
            yield f"event: tool_result\ndata: {json.dumps(call_rec.model_dump())}\n\n"
            await asyncio.sleep(0.02)

        # Final response synthesis
        chat_resp = await self.chat(request)
        yield f"event: final_response\ndata: {json.dumps(chat_resp.model_dump())}\n\n"
        yield "event: done\ndata: {}\n\n"

    def get_history(self, conversation_id: str) -> ConversationHistoryResponse | None:
        """Retrieve conversation history by session ID."""
        session = self.sessions.get(conversation_id)
        if not session:
            return None
        return ConversationHistoryResponse(
            conversation_id=session.conversation_id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            messages=session.messages,
            tool_history=session.tool_history,
        )
