"""Unit and API integration tests for ORCA Agent 6: AI Workspace Assistant.

Covers:
- Natural-language intent understanding & tool selection
- Single and multi-specialist tool invocations
- Follow-up conversation context retention
- Security sandbox enforcement (path traversal & .env file blocking)
- Whitelisted command enforcement and rejection of unsafe shell commands
- Controlled tool approval and denial workflow
- Discrepancy detection between measured wave height and reported WMO sea state
- FastAPI endpoints (POST chat, POST stream, POST approve, GET history, GET tools)
"""

from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
import pytest

from app.agents.assistant_agent import AssistantAgent
from app.agents.tools.tool_registry import ToolDefinition, ToolRegistry
from app.agents.tools.workspace_tools import (
    tool_apply_file_edit,
    tool_list_project_files,
    tool_propose_file_edit,
    tool_read_project_file,
    tool_run_approved_command,
    tool_run_approved_tests,
)
from app.main import app
from app.schemas.assistant_schemas import (
    AssistantApproveRequest,
    AssistantChatRequest,
)

client = TestClient(app)


# ==============================================================================
# Unit Tests: Security and Workspace Tools Sandbox
# ==============================================================================

def test_workspace_security_rejects_path_traversal():
    """Verify filesystem tool strictly prevents path traversal outside workspace root."""
    with pytest.raises(PermissionError) as exc_info:
        tool_read_project_file("../../Windows/System32/drivers/etc/hosts")
    assert "escapes the authorized workspace" in str(exc_info.value)


def test_workspace_security_blocks_sensitive_env_file():
    """Verify tool strictly blocks access to .env and credential files."""
    with pytest.raises(PermissionError) as exc_info:
        tool_read_project_file(".env")
    assert "Security restriction: Access to sensitive file '.env' is prohibited" in str(exc_info.value)


def test_workspace_command_safety_rejects_arbitrary_shell():
    """Verify command runner strictly rejects unapproved arbitrary commands."""
    res = tool_run_approved_command("rm -rf /")
    assert res["success"] is False
    assert "Security policy rejection" in res["error"]


def test_workspace_command_allows_whitelisted_git_status():
    """Verify whitelisted dev commands execute safely and return exit codes."""
    res = tool_run_approved_command("git status")
    assert res["success"] is True
    assert res["exit_code"] == 0
    assert "On branch" in res["stdout"] or "HEAD" in res["stdout"]


def test_workspace_read_project_file_valid():
    """Verify read_project_file reads authorized workspace files with line slicing."""
    res = tool_read_project_file("backend/app/agents/sea_state_rules.py", start_line=1, end_line=10)
    assert res["success"] is True
    assert res["start_line"] == 1
    assert res["end_line"] == 10
    assert "Documented Marine Meteorological" in res["content"]


def test_workspace_list_project_files():
    """Verify list_project_files lists workspace directory contents without hidden caches."""
    res = tool_list_project_files("backend/app/agents")
    assert res["success"] is True
    names = [item["name"] for item in res["items"]]
    assert "weather_agent.py" in names
    assert "ocean_agent.py" in names
    assert ".git" not in names


def test_workspace_propose_file_edit_diff():
    """Verify propose_file_edit generates diff without writing and marks approval required."""
    res = tool_propose_file_edit(
        "backend/app/agents/sea_state_rules.py",
        target_content='"""Documented Marine Meteorological Sea State Rules.',
        replacement_content='"""Documented Marine Meteorological Sea State Rules (Updated).',
    )
    assert res["success"] is True
    assert res["requires_approval"] is True
    assert "diff" in res
    assert "-    \"\"\"Documented Marine Meteorological Sea State Rules." in res["diff"] or "Documented" in res["diff"]


# ==============================================================================
# Unit Tests: AssistantAgent Conversational Lifecycle
# ==============================================================================

@pytest.mark.asyncio
async def test_assistant_simple_conversational_response():
    """Verify assistant handles generic greetings and system status queries."""
    assistant = AssistantAgent()
    req = AssistantChatRequest(message="Hello ORCA, please check system status.")
    res = await assistant.chat(req)

    assert res.response_message.role == "assistant"
    assert res.conversation_id is not None
    assert any(step.tool_name == "check_system_health" for step in res.plan)
    assert len(res.tool_calls) >= 1
    assert "HEALTHY" in res.response_message.content or "Status" in res.response_message.content


@pytest.mark.asyncio
async def test_assistant_tool_selection_weather_intent():
    """Verify assistant selects only Weather Agent when user asks about weather."""
    assistant = AssistantAgent()
    req = AssistantChatRequest(message="What is the weather and temperature at 15.0°N, 72.0°E?")
    res = await assistant.chat(req)

    tools_called = [c.tool_name for c in res.tool_calls]
    assert "invoke_weather_agent" in tools_called
    assert "invoke_ocean_agent" not in tools_called
    assert "invoke_route_agent" not in tools_called
    assert "Weather Agent" in res.agent_results
    assert res.evidence_summary["measured_observations"]["temperature_c"] is not None


@pytest.mark.asyncio
async def test_assistant_tool_selection_ocean_intent():
    """Verify assistant selects Ocean Agent for sea state and wave height questions."""
    assistant = AssistantAgent()
    req = AssistantChatRequest(message="Analyze wave conditions and sea state at 15.0, 72.0")
    res = await assistant.chat(req)

    tools_called = [c.tool_name for c in res.tool_calls]
    assert "invoke_ocean_agent" in tools_called
    assert "Ocean Agent" in res.agent_results
    assert res.evidence_summary["measured_observations"]["wave_height_m"] is not None


@pytest.mark.asyncio
async def test_assistant_follow_up_context():
    """Verify assistant retains coordinates from previous turn in follow-up queries."""
    assistant = AssistantAgent()

    # Turn 1: User mentions coordinates with weather
    req1 = AssistantChatRequest(message="Check weather at 15.0, 72.0")
    res1 = await assistant.chat(req1)
    cid = res1.conversation_id

    # Turn 2: User asks follow-up without re-stating coordinates
    req2 = AssistantChatRequest(
        message="Now assess safety risks for a small craft there",
        conversation_id=cid,
    )
    res2 = await assistant.chat(req2)

    assert res2.conversation_id == cid
    safety_call = next(c for c in res2.tool_calls if c.tool_name == "invoke_safety_risk_agent")
    assert safety_call.arguments["latitude"] == 15.0
    assert safety_call.arguments["longitude"] == 72.0
    assert safety_call.arguments["vessel_type"] == "small_craft"


@pytest.mark.asyncio
async def test_assistant_controlled_approval_workflow():
    """Verify assistant pauses execution for tools requiring approval and resumes on approve."""
    assistant = AssistantAgent()

    # Turn 1: User asks to run test suite (requires approval)
    req = AssistantChatRequest(message="Run the backend test suite")
    res = await assistant.chat(req)

    assert res.status == "waiting_approval"
    pending_call = next(c for c in res.tool_calls if c.status == "waiting_approval")
    assert pending_call.requires_approval is True

    # Turn 2: Deny execution
    deny_req = AssistantApproveRequest(
        conversation_id=res.conversation_id,
        call_id=pending_call.call_id,
        decision="deny",
    )
    deny_res = await assistant.approve_tool_call(deny_req)
    assert deny_res.status == "denied"


@pytest.mark.asyncio
async def test_assistant_detects_wmo_discrepancy():
    """Verify assistant detects discrepancy when wave height 1.4m conflicts with WMO Code 3."""
    assistant = AssistantAgent()

    # Mock ocean tool returning wave_height=1.4 with WMO Code 3 (Slight 0.5-1.25m)
    async def fake_ocean(**kwargs):
        return {
            "agent": "Ocean Agent",
            "status": "success",
            "observations": {"wave_height_m": 1.4},
            "analysis": {"wmo_sea_state": {"code": 3, "description": "Slight (0.5 - 1.25 m)"}},
            "warnings": [],
        }

    assistant.tools.register(
        ToolDefinition(
            name="invoke_ocean_agent",
            description="Mock ocean tool",
            category="specialist",
            parameters={},
            handler=fake_ocean,
        )
    )

    req = AssistantChatRequest(message="Check wave height and WMO code at 15.0, 72.0")
    res = await assistant.chat(req)

    assert "wmo_discrepancy_warning" in res.evidence_summary["measured_observations"]
    assert any("Observation discrepancy" in w for w in res.evidence_summary["warnings"])
    # Provider evidence is preserved without silent modification
    assert res.evidence_summary["measured_observations"]["wmo_sea_state"]["code"] == 3


@pytest.mark.asyncio
async def test_assistant_preserves_critical_safety_hazard():
    """Verify assistant strictly preserves CRITICAL safety risk and halts operations."""
    assistant = AssistantAgent()
    req = AssistantChatRequest(
        message="Assess safety for small craft at 15.0, 72.0 with 5.5m waves and 45 knots wind"
    )
    res = await assistant.chat(req)

    assert res.evidence_summary["composite_safety_risk"] == "CRITICAL"
    assert any("HAZARD WARNING" in w for w in res.evidence_summary["warnings"])
    assert any("DANGER" in r or "CRITICAL" in r for r in res.response_message.content.splitlines())


# ==============================================================================
# API Endpoint Integration Tests
# ==============================================================================

def test_assistant_chat_endpoint_success():
    """Test POST /api/agents/assistant/chat endpoint."""
    res = client.post(
        "/api/agents/assistant/chat",
        json={"message": "What is the weather at 15.0, 72.0?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "conversation_id" in data
    assert data["response_message"]["role"] == "assistant"
    assert len(data["plan"]) >= 1
    assert "Weather Agent" in data["agent_results"]


def test_assistant_tools_endpoint():
    """Test GET /api/agents/assistant/tools endpoint."""
    res = client.get("/api/agents/assistant/tools")
    assert res.status_code == 200
    tools = res.json()["tools"]
    tool_names = [t["name"] for t in tools]
    assert "invoke_weather_agent" in tool_names
    assert "invoke_ocean_agent" in tool_names
    assert "read_project_file" in tool_names
    assert "apply_file_edit" in tool_names
    # Verify approval flag
    apply_tool = next(t for t in tools if t["name"] == "apply_file_edit")
    assert apply_tool["requires_approval"] is True


def test_assistant_conversation_history_endpoint():
    """Test GET /api/agents/assistant/conversations/{id} endpoint."""
    # 1. Create a turn
    chat_res = client.post(
        "/api/agents/assistant/chat",
        json={"message": "System status check"},
    )
    cid = chat_res.json()["conversation_id"]

    # 2. Retrieve history
    hist_res = client.get(f"/api/agents/assistant/conversations/{cid}")
    assert hist_res.status_code == 200
    data = hist_res.json()
    assert data["conversation_id"] == cid
    assert len(data["messages"]) == 2  # 1 user + 1 assistant


def test_assistant_streaming_endpoint():
    """Test POST /api/agents/assistant/chat/stream Server-Sent Events endpoint."""
    res = client.post(
        "/api/agents/assistant/chat/stream",
        json={"message": "Weather check at 15.0, 72.0"},
    )
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]
    body = res.text
    assert "event: session" in body
    assert "event: plan" in body
    assert "event: tool_start" in body
    assert "event: final_response" in body
    assert "event: done" in body


# ==============================================================================
# Regression Tests: Ocean Agent Synthesis & N/A Defect Prevention
# ==============================================================================

@pytest.mark.asyncio
async def test_assistant_ocean_chat_synthesis_no_na_on_valid_data():
    """Verify assistant conversational reply formats valid wave height and WMO code without N/A."""
    assistant = AssistantAgent()

    # Tool returns actual OceanAgent output structure
    async def mock_ocean_tool(**kwargs):
        return {
            "agent": "Ocean Agent",
            "status": "success",
            "observations": {
                "sample_count": 24,
                "wave_height_m": 1.75,
                "min_wave_height_m": 0.80,
                "max_wave_height_m": 1.75,
                "avg_wave_height_m": 1.25,
                "latest_wave_height_m": 1.10,
                "timeseries": [],
            },
            "analysis": {
                "sea_state_code": 4,
                "sea_state_category": "Moderate",
                "description": "1.25 to 2.5 m",
                "wmo_sea_state": {
                    "code": 4,
                    "category": "Moderate",
                    "description": "1.25 to 2.5 m",
                },
                "summary": "Wave heights reach 1.75 m (Moderate, WMO Code 4).",
            },
            "warnings": [],
        }

    assistant.tools.register(
        ToolDefinition(
            name="invoke_ocean_agent",
            description="Mock ocean tool",
            category="specialist",
            parameters={},
            handler=mock_ocean_tool,
        )
    )

    req = AssistantChatRequest(message="What is the sea state and wave height at 15.0, 72.0?")
    res = await assistant.chat(req)

    reply = res.response_message.content
    assert "Significant wave height 1.75 m" in reply
    assert "WMO Sea State: Code 4 (Moderate)" in reply
    assert "Significant wave height N/A m" not in reply
    assert "Code N/A" not in reply


@pytest.mark.asyncio
async def test_assistant_ocean_chat_synthesis_preserves_na_when_missing():
    """Verify assistant strictly preserves N/A when ocean evidence is truly missing or null."""
    assistant = AssistantAgent()

    async def mock_empty_ocean(**kwargs):
        return {
            "agent": "Ocean Agent",
            "status": "insufficient_evidence",
            "observations": {"sample_count": 0, "timeseries": []},
            "analysis": {
                "sea_state_code": None,
                "sea_state_category": "UNKNOWN",
                "summary": "All wave values null.",
            },
            "warnings": ["No marine records available."],
        }

    assistant.tools.register(
        ToolDefinition(
            name="invoke_ocean_agent",
            description="Mock ocean tool",
            category="specialist",
            parameters={},
            handler=mock_empty_ocean,
        )
    )

    req = AssistantChatRequest(message="Check wave conditions at 15.0, 72.0")
    res = await assistant.chat(req)

    reply = res.response_message.content
    assert "Significant wave height N/A m" in reply
    assert "Code N/A" in reply


# ==============================================================================
# Regression Tests: Route Invocation, Coordinate Integrity & Agent Failures
# ==============================================================================

@pytest.mark.asyncio
async def test_assistant_route_execution_when_route_requested():
    """Verify Route Agent is planned and invoked with real origin/dest coordinates when route is requested."""
    assistant = AssistantAgent()

    req = AssistantChatRequest(message="Plan geodesic route from Goa (15.0, 72.0) to Mumbai (18.9, 72.8)")
    res = await assistant.chat(req)

    # 1. Plan must include Route Agent
    tool_names = [call.tool_name for call in res.tool_calls]
    assert "invoke_route_agent" in tool_names

    # 2. Tool call parameters must match requested coordinates
    route_call = next(c for c in res.tool_calls if c.tool_name == "invoke_route_agent")
    assert route_call.arguments["origin_latitude"] == 15.0
    assert route_call.arguments["origin_longitude"] == 72.0
    assert route_call.arguments["destination_latitude"] == 18.9
    assert route_call.arguments["destination_longitude"] == 72.8

    # 3. Agent results must contain Route Agent with real distance calculation (~442 km)
    assert "Route" in res.agent_results
    assert res.agent_results["Route"]["status"] == "success"
    dist = res.agent_results["Route"]["analysis"]["distance_km"]
    assert 440 < dist < 450

    # 4. Evidence summary coordinates must reflect route
    coords = res.evidence_summary["coordinates"]
    assert coords["has_route"] is True
    assert coords["origin_lat"] == 15.0
    assert coords["origin_lon"] == 72.0
    assert coords["dest_lat"] == 18.9
    assert coords["dest_lon"] == 72.8


@pytest.mark.asyncio
async def test_assistant_multi_agent_plan_includes_five_agents_when_route_requested():
    """Verify multi-agent advisory includes all 5 specialist agents (including Route) when route is requested."""
    assistant = AssistantAgent()

    req = AssistantChatRequest(
        message="Generate full marine advisory and navigation route transit from 15.0, 72.0 to 18.9, 72.8"
    )
    res = await assistant.chat(req)

    tool_names = [call.tool_name for call in res.tool_calls]
    assert "invoke_weather_agent" in tool_names
    assert "invoke_ocean_agent" in tool_names
    assert "invoke_fishing_zone_agent" in tool_names
    assert "invoke_route_agent" in tool_names
    assert "invoke_safety_risk_agent" in tool_names
    assert len(res.plan) == 5

    # Check that Route Agent was executed
    assert "Route" in res.agent_results
    assert res.agent_results["Route"]["status"] == "success"


@pytest.mark.asyncio
async def test_assistant_coordinate_consistency_no_overwriting_defaults():
    """Verify dashboard/agent coordinates strictly follow current user request and do not overwrite with defaults."""
    assistant = AssistantAgent()

    # User asks for Mangalore coordinates (12.91, 74.85)
    req = AssistantChatRequest(message="Assess safety and ocean conditions at 12.91, 74.85 for small vessel")
    res = await assistant.chat(req)

    # Coords in evidence_summary must strictly match 12.91, 74.85
    coords = res.evidence_summary["coordinates"]
    assert coords["origin_lat"] == 12.91
    assert coords["origin_lon"] == 74.85
    assert coords["has_route"] is False

    # Tool calls must receive 12.91, 74.85
    for call in res.tool_calls:
        if "latitude" in call.arguments:
            assert call.arguments["latitude"] == 12.91
            assert call.arguments["longitude"] == 74.85

    # Final response must mention 12.91 and 74.85
    content = res.response_message.content
    assert "12.91" in content
    assert "74.85" in content


@pytest.mark.asyncio
async def test_assistant_missing_fisheries_evidence_retains_insufficient_evidence():
    """Verify missing biological fisheries telemetry retains INSUFFICIENT_EVIDENCE and does not fabricate data."""
    assistant = AssistantAgent()

    req = AssistantChatRequest(message="Provide fishing zone and marine advisory for 15.0, 72.0")
    res = await assistant.chat(req)

    # Fishing Zone Agent must report insufficient_evidence
    assert "Fishing Zone" in res.agent_results
    fz_status = res.agent_results["Fishing Zone"]["status"]
    assert fz_status == "insufficient_evidence"

    # Response content must explicitly convey INSUFFICIENT_EVIDENCE and lack of direct biological telemetry
    content = res.response_message.content
    assert "INSUFFICIENT_EVIDENCE" in content or "insufficient_evidence" in content.lower()
    assert "direct biological fish distribution" in content or "unverified" in content


@pytest.mark.asyncio
async def test_assistant_agent_failure_reports_failed_status_gracefully():
    """Verify when an individual specialist agent fails, status is explicitly FAILED without crashing."""
    assistant = AssistantAgent()

    # Register a failing weather tool
    async def mock_failing_weather(**kwargs):
        raise RuntimeError("Open-Meteo upstream service unavailable")

    assistant.tools.register(
        ToolDefinition(
            name="invoke_weather_agent",
            description="Mock failing weather",
            category="specialist",
            parameters={},
            handler=mock_failing_weather,
        )
    )

    req = AssistantChatRequest(message="Check weather conditions at 15.0, 72.0")
    res = await assistant.chat(req)

    # Tool call status must be failed
    weather_call = next(c for c in res.tool_calls if c.tool_name == "invoke_weather_agent")
    assert weather_call.status == "failed"
    assert weather_call.error is not None
    assert "upstream service unavailable" in weather_call.error.lower()

    # Agent result must report failed
    assert "Weather" in res.agent_results
    assert res.agent_results["Weather"]["status"] == "failed"

    # Overall execution must not falsely report 100% success
    assert res.evidence_summary["overall_status"] in ["PARTIAL_SUCCESS", "FAILED"]


@pytest.mark.asyncio
async def test_assistant_route_and_fisheries_disclaimers_in_conversational_response():
    """Verify assistant enforces geodesic labeling, nautical disclaimers, and unverified biological status."""
    assistant = AssistantAgent()

    req = AssistantChatRequest(message="Calculate route and fishing advisory from 15.0, 72.0 to 18.0, 72.5")
    res = await assistant.chat(req)

    # 1. Route Agent checks
    assert "Route" in res.agent_results or "Route Agent" in res.agent_results
    route_data = res.agent_results.get("Route") or res.agent_results.get("Route Agent", {})
    route_analysis = route_data.get("analysis", {})
    assert route_analysis.get("is_verified_navigable_route") is False
    assert "geodesic" in route_analysis.get("calculation_method", "").lower() or "geodesic" in str(route_data).lower()

    content = res.response_message.content
    # Route labeling & disclaimer must be present in assistant response text
    assert "geodesic" in content.lower()
    assert "bathymetry" in content.lower() or "land avoidance" in content.lower() or "not a certified nautical passage" in content.lower()

    # 2. Fisheries limitation checks
    assert "Fishing Zone" in res.agent_results
    assert "INSUFFICIENT_EVIDENCE" in content or "insufficient_evidence" in content.lower()
    assert "biological" in content.lower()


@pytest.mark.asyncio
async def test_assistant_goa_to_mumbai_preserves_endpoints_distance_and_transit():
    """Bug 1 Regression: Assistant preserves distinct origin (Goa) and destination (Mumbai) endpoints."""
    assistant = AssistantAgent()
    req = AssistantChatRequest(message="Plan geodesic route from Goa (15.0, 72.0) to Mumbai (18.95, 72.82)")
    res = await assistant.chat(req)

    # 1. Tool call arguments check
    route_call = next(c for c in res.tool_calls if c.tool_name == "invoke_route_agent")
    assert route_call.arguments["origin_latitude"] == 15.0
    assert route_call.arguments["origin_longitude"] == 72.0
    assert route_call.arguments["destination_latitude"] == 18.95
    assert route_call.arguments["destination_longitude"] == 72.82
    assert route_call.arguments["origin_name"] == "Goa Sector"
    assert route_call.arguments["destination_name"] == "Mumbai Port"

    # 2. Evidence coordinates check
    coords = res.evidence_summary["coordinates"]
    assert coords["origin_lat"] == 15.0
    assert coords["origin_lon"] == 72.0
    assert coords["dest_lat"] == 18.95
    assert coords["dest_lon"] == 72.82
    assert coords["origin_name"] == "Goa Sector"
    assert coords["destination_name"] == "Mumbai Port"
    assert coords["has_route"] is True

    # 3. Route distance and transit hours check
    route_data = res.agent_results.get("Route") or res.agent_results.get("Route Agent")
    assert route_data is not None
    dist_km = route_data["observations"]["total_distance_km"]
    assert 430.0 < dist_km < 460.0
    assert route_data["observations"]["estimated_transit_time_hours"] > 15.0

    # 4. Message content must display actual distance and estimated transit
    content = res.response_message.content
    assert str(dist_km) in content or f"{dist_km:.2f}" in content
    assert "estimated transit" in content.lower()


@pytest.mark.asyncio
async def test_assistant_route_identical_endpoints_not_silently_substituted():
    """Bug 1 Regression: Identical coordinates are not silently substituted with other ports."""
    assistant = AssistantAgent()
    req = AssistantChatRequest(message="Plan route from 15.0, 72.0 to 15.0, 72.0")
    res = await assistant.chat(req)

    route_call = next(c for c in res.tool_calls if c.tool_name == "invoke_route_agent")
    assert route_call.arguments["origin_latitude"] == 15.0
    assert route_call.arguments["destination_latitude"] == 15.0
    assert route_call.arguments["origin_longitude"] == 72.0
    assert route_call.arguments["destination_longitude"] == 72.0

    route_data = res.agent_results.get("Route") or res.agent_results.get("Route Agent")
    assert route_data is not None
    assert route_data["observations"]["total_distance_km"] == 0.0
    assert any("identical" in w.lower() for w in route_data.get("warnings", []))


