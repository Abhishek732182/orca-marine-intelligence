"""Unit tests for LLM-based descriptive planning, specialist allowlist enforcement,
clarification handling, synthesis grounding, failure handling, and safety state preservation.
"""

from unittest.mock import AsyncMock, patch
import httpx
import pytest
from fastapi.testclient import TestClient

from app.agents.mission_planner import (
    ALLOWED_SPECIALIST_AGENTS,
    StructuredPlanSchema,
    deterministic_plan_mission,
    plan_mission_request,
)
from app.agents.mission_synthesizer import (
    generate_deterministic_synthesis,
    synthesize_mission_advisory,
)
from app.agents.orchestrator_agent import OrchestratorAgent, LEGAL_DISCLAIMER
from app.main import app
from app.schemas.agent_schemas import (
    FishingZoneAnalyzeResponse,
    OceanAnalyzeResponse,
    OrchestratorAnalyzeRequest,
    RouteAnalyzeResponse,
    SafetyRiskAnalyzeResponse,
    WeatherAnalyzeResponse,
)

client = TestClient(app)


def _dummy_weather(temp=27.5, wind_kts=18.0, precip=0.0):
    return WeatherAnalyzeResponse(
        agent="Weather Agent",
        status="success",
        location={"location_name": "Goa Waters", "latitude": 15.0, "longitude": 72.0},
        data_source={"provider": "Open-Meteo Weather"},
        observations={
            "temperature_c": temp,
            "wind_speed_knots": wind_kts,
            "wind_direction_deg": 260.0,
            "precipitation_mm": precip,
        },
        forecast=[],
        analysis={"wind_regime": "Fresh breeze"},
        warnings=[],
    )


def _dummy_ocean(wave_h=1.8, wmo_code=4, wmo_desc="Moderate (1.25 - 2.5 m)"):
    return OceanAnalyzeResponse(
        agent="Ocean Agent",
        status="success",
        location={"location_name": "Goa Waters", "latitude": 15.0, "longitude": 72.0},
        data_source={"provider": "Open-Meteo Marine"},
        observations={"wave_height_m": wave_h, "sample_count": 24},
        analysis={
            "sea_state_code": wmo_code,
            "sea_state_category": "Moderate",
            "wmo_sea_state": {"code": wmo_code, "category": "Moderate", "description": wmo_desc},
        },
        warnings=[],
    )


def _dummy_fishing():
    return FishingZoneAnalyzeResponse(
        agent="Fishing Zone Agent",
        status="insufficient_evidence",
        location={"location_name": "Goa Waters", "latitude": 15.0, "longitude": 72.0},
        data_source={"provider": "Open-Meteo Marine"},
        observations={"wave_height_m": 1.8},
        analysis={
            "zone_suitability": "INSUFFICIENT_EVIDENCE",
            "operational_feasibility": "FAVORABLE",
            "verified_fish_distribution": {
                "status": "UNVERIFIED",
                "biomass_data_available": False,
                "catch_probability": None,
                "statement": "Direct fish location telemetry is unavailable from numerical models.",
            },
        },
        warnings=["Direct pelagic fish biomass is unverified."],
    )


def _dummy_safety(risk_category="MODERATE", risk_score=45):
    return SafetyRiskAnalyzeResponse(
        agent="Safety/Risk Agent",
        status="success",
        location={"location_name": "Goa Waters", "latitude": 15.0, "longitude": 72.0},
        data_source={"providers_attempted": ["Open-Meteo Marine", "Open-Meteo Weather"]},
        observations={"wave_height_m": 1.8, "wind_speed_knots": 18.0, "precipitation_mm": 0.0},
        analysis={
            "risk_category": risk_category,
            "risk_score": risk_score,
            "risk_reasons": ["Moderate wave heights present within craft tolerance."],
            "recommendations": ["Exercise watchfulness in offshore transit corridor."],
        },
        warnings=[],
    )


def _dummy_route(dist_km=442.0, dist_nm=238.7, transit_hours=19.9):
    return RouteAnalyzeResponse(
        agent="Route Agent",
        status="success",
        location={"origin": "Goa Waters", "destination": "Mumbai Port"},
        data_source={"calculation_method": "Haversine Great-Circle geodesic formula"},
        observations={"total_distance_km": dist_km, "total_distance_nm": dist_nm, "waypoint_count": 2},
        analysis={"estimated_transit_hours": transit_hours},
        warnings=["Straight-line geodesic distance only; does not reflect navigable marine channels."],
    )


# ==============================================================================
# 1. Natural Language Planning & Intent Extraction
# ==============================================================================

@pytest.mark.asyncio
async def test_natural_language_planning_extracts_intent_and_coordinates():
    """Verify natural-language request extracts intent, coordinates, vessel type, and window."""
    query = "Plan a fishing trip for mackerel from Goa (15.0, 72.0) with a 48 hour window for a trawler."
    plan, mode = await plan_mission_request(query, {})

    assert plan.user_objective == "fishing"
    assert plan.origin_latitude == 15.0
    assert plan.origin_longitude == 72.0
    assert plan.forecast_time_window_hours == 48
    assert plan.vessel_type == "trawler"
    assert plan.target_species == "Mackerel"
    assert "fishing_zone" in plan.planned_agents
    assert "weather" in plan.planned_agents
    assert "ocean" in plan.planned_agents
    assert "safety_risk" in plan.planned_agents
    assert plan.clarification_needed is False


# ==============================================================================
# 2. Specialist Allowlist Enforcement
# ==============================================================================

def test_specialist_agent_allowlist_enforcement():
    """Verify any agent/tool name outside the 5 specialists is strictly rejected."""
    raw_agents = ["weather", "ocean", "unauthorized_code_exec", "sql_tool", "fishing_zone", "hacker_agent"]
    validated = StructuredPlanSchema.validate_allowlist(raw_agents)

    assert set(validated).issubset(ALLOWED_SPECIALIST_AGENTS)
    assert "weather" in validated
    assert "ocean" in validated
    assert "fishing_zone" in validated
    assert "unauthorized_code_exec" not in validated
    assert "sql_tool" not in validated
    assert "hacker_agent" not in validated


# ==============================================================================
# 3. Parameter Validation and Clamping
# ==============================================================================

def test_parameter_validation_and_clamping():
    """Verify out-of-bounds coordinates and invalid windows are clamped or rejected."""
    # Out-of-bounds coordinates raise validation error in Pydantic schema
    with pytest.raises(Exception):
        StructuredPlanSchema(origin_latitude=95.0, origin_longitude=72.0)

    # Window clamping in deterministic planner
    plan = deterministic_plan_mission(
        "Check weather at 15.0, 72.0 for 500 hours",
        {"latitude": 15.0, "longitude": 72.0, "forecast_time_window_hours": 500},
    )
    assert plan.forecast_time_window_hours <= 168


# ==============================================================================
# 4. Clarification Request on Missing Coordinates
# ==============================================================================

@pytest.mark.asyncio
async def test_clarification_request_when_coordinates_missing():
    """Verify query without location asks for clarification and never invents coordinates."""
    orchestrator = OrchestratorAgent()
    req = OrchestratorAnalyzeRequest(query="What is the current wave height and sea state?")
    res = await orchestrator.analyze(req)

    assert res.status == "clarification_needed"
    assert res.clarification_needed is True
    assert "origin_coordinates" in res.missing_inputs
    assert res.clarification_prompt is not None
    assert "geographical coordinates" in res.clarification_prompt.lower()
    # Confirm no fake coordinates were invented in origin location
    assert res.location.get("origin") is None or (res.location["origin"]["latitude"] is None)
    # Composite safety risk cannot be declared LOW without evidence
    assert res.composite_safety_risk["risk_category"] == "UNKNOWN / INSUFFICIENT EVIDENCE"


# ==============================================================================
# 5. Clarification Request on Missing Route Destination
# ==============================================================================

@pytest.mark.asyncio
async def test_clarification_request_for_passage_planning_without_destination():
    """Verify conversational passage planning query without destination asks for clarification."""
    orchestrator = OrchestratorAgent()
    req = OrchestratorAnalyzeRequest(query="Calculate route passage from Goa (15.0, 72.0)")
    res = await orchestrator.analyze(req)

    assert res.status == "clarification_needed"
    assert res.clarification_needed is True
    assert "destination_coordinates" in res.missing_inputs
    assert res.clarification_prompt is not None
    assert "destination endpoint" in res.clarification_prompt.lower() or "destination" in res.clarification_prompt.lower()


# ==============================================================================
# 6. Synthesis Grounding: Guardrails Reject Hallucinations
# ==============================================================================

@pytest.mark.asyncio
async def test_synthesis_guardrails_reject_hallucinated_fish_and_safety():
    """Verify synthesis guardrails discard model output if it invents catch rates or marks critical risk safe."""
    hallucinated_text = "Good news! Catch probability: 85% with 20 tons/km biomass. It is safe to sail."

    with patch("app.agents.mission_synthesizer.call_chat_llm", AsyncMock(return_value=(hallucinated_text, "llm"))):
        text, mode = await synthesize_mission_advisory(
            location_name="Offshore Goa",
            latitude=15.0,
            longitude=72.0,
            user_objective="fishing",
            vessel_type="small_craft",
            measured_observations={"wave_height_m": 4.5},
            derived_estimates={},
            composite_safety_risk={"risk_category": "CRITICAL", "status_headline": "DANGER"},
            warnings=["Severe gale"],
            missing_evidence=["Direct fish biomass unverified"],
            errors={},
            recommendations=["Stay in port"],
        )

        # The guardrail rejects the hallucinated LLM text and falls back to deterministic synthesis
        assert mode == "deterministic"
        assert "Catch probability: 85%" not in text
        assert "CRITICAL" in text


# ==============================================================================
# 7. Discrepancy Detection & Conflict Preservation
# ==============================================================================

@pytest.mark.asyncio
async def test_conflicting_results_observation_discrepancy_warning():
    """Verify 1.4m wave height conflicting with WMO Code 3 is highlighted without dropping evidence."""
    orchestrator = OrchestratorAgent(
        weather_agent=AsyncMock(analyze=AsyncMock(return_value=_dummy_weather())),
        ocean_agent=AsyncMock(analyze=AsyncMock(return_value=_dummy_ocean(wave_h=1.4, wmo_code=3, wmo_desc="Slight"))),
        safety_risk_agent=AsyncMock(analyze=AsyncMock(return_value=_dummy_safety())),
    )

    req = OrchestratorAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        user_objective="general_maritime",
    )
    res = await orchestrator.analyze(req)

    assert any("Observation discrepancy" in w for w in res.warnings)
    assert res.measured_observations["wmo_sea_state_code"] == 3
    assert res.measured_observations["wave_height_m"] == 1.4


# ==============================================================================
# 8. Partial Tool Failure Handling
# ==============================================================================

@pytest.mark.asyncio
async def test_partial_tool_failure_handling():
    """Verify that when one specialist fails, orchestrator reports partial_failure and preserves other results."""
    orchestrator = OrchestratorAgent(
        weather_agent=AsyncMock(analyze=AsyncMock(side_effect=httpx.ConnectError("Open-Meteo connection refused"))),
        ocean_agent=AsyncMock(analyze=AsyncMock(return_value=_dummy_ocean())),
        safety_risk_agent=AsyncMock(analyze=AsyncMock(return_value=_dummy_safety())),
    )

    req = OrchestratorAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        user_objective="general_maritime",
    )
    res = await orchestrator.analyze(req)

    assert res.status == "partial_failure"
    assert "weather" in res.errors
    assert "ocean" in res.individual_agent_results
    assert res.individual_agent_results["ocean"]["status"] == "success"


# ==============================================================================
# 9. LLM Failure & Timeout Deterministic Fallback
# ==============================================================================

@pytest.mark.asyncio
async def test_llm_failure_and_timeout_deterministic_fallback():
    """Verify LLM timeout cleanly triggers deterministic fallback without crashing."""
    with patch("app.agents.llm_client.call_chat_llm", AsyncMock(side_effect=httpx.TimeoutException("LLM gateway timeout"))):
        orchestrator = OrchestratorAgent(
            weather_agent=AsyncMock(analyze=AsyncMock(return_value=_dummy_weather())),
            ocean_agent=AsyncMock(analyze=AsyncMock(return_value=_dummy_ocean())),
            safety_risk_agent=AsyncMock(analyze=AsyncMock(return_value=_dummy_safety())),
        )

        req = OrchestratorAnalyzeRequest(
            latitude=15.0,
            longitude=72.0,
            query="Evaluate marine conditions at Goa (15.0, 72.0)",
        )
        res = await orchestrator.analyze(req)

        assert res.status == "success"
        assert res.generation_mode == "deterministic"
        assert res.descriptive_synthesis is not None
        assert "ORCA Mission" in res.descriptive_synthesis or "Measured" in res.descriptive_synthesis


# ==============================================================================
# 10. Safety State Preservation
# ==============================================================================

@pytest.mark.asyncio
async def test_safety_state_preservation_critical_and_missing_telemetry():
    """Verify CRITICAL risk is never downgraded and missing telemetry is never classified as LOW/safe."""
    # Scenario A: CRITICAL safety reported
    orchestrator_crit = OrchestratorAgent(
        weather_agent=AsyncMock(analyze=AsyncMock(return_value=_dummy_weather())),
        ocean_agent=AsyncMock(analyze=AsyncMock(return_value=_dummy_ocean())),
        safety_risk_agent=AsyncMock(analyze=AsyncMock(return_value=_dummy_safety(risk_category="CRITICAL", risk_score=95))),
    )
    res_crit = await orchestrator_crit.analyze(OrchestratorAnalyzeRequest(latitude=15.0, longitude=72.0))
    assert res_crit.composite_safety_risk["risk_category"] == "CRITICAL"
    assert any("DANGER" in r or "CRITICAL" in r for r in res_crit.recommendations)

    # Scenario B: Missing wave telemetry prevents declaring conditions safe
    orchestrator_missing = OrchestratorAgent(
        weather_agent=AsyncMock(analyze=AsyncMock(return_value=_dummy_weather())),
        ocean_agent=AsyncMock(analyze=AsyncMock(return_value=OceanAnalyzeResponse(
            agent="Ocean Agent",
            status="insufficient_evidence",
            location={"latitude": 15.0, "longitude": 72.0},
            data_source={},
            observations={"wave_height_m": None, "sample_count": 0},
            analysis={},
        ))),
        safety_risk_agent=AsyncMock(analyze=AsyncMock(return_value=_dummy_safety(risk_category="LOW", risk_score=10))),
    )
    res_missing = await orchestrator_missing.analyze(OrchestratorAnalyzeRequest(latitude=15.0, longitude=72.0))
    # When wave telemetry is missing, composite risk CANNOT be LOW
    assert res_missing.composite_safety_risk["risk_category"] != "LOW"
    assert "INSUFFICIENT" in res_missing.composite_safety_risk["risk_category"]


# ==============================================================================
# 11. API Endpoint Integration with Query Parameter
# ==============================================================================

def test_orchestrator_api_endpoint_with_natural_language_query(monkeypatch):
    """Verify POST /api/agents/orchestrator/analyze accepts natural-language query field."""
    from app.api.routes.agents import orchestrator

    monkeypatch.setattr(orchestrator.agent, "weather_agent", AsyncMock(analyze=AsyncMock(return_value=_dummy_weather())))
    monkeypatch.setattr(orchestrator.agent, "ocean_agent", AsyncMock(analyze=AsyncMock(return_value=_dummy_ocean())))
    monkeypatch.setattr(orchestrator.agent, "safety_risk_agent", AsyncMock(analyze=AsyncMock(return_value=_dummy_safety())))

    response = client.post(
        "/api/agents/orchestrator/analyze",
        json={
            "query": "Assess sea state and weather for Goa Sector (15.0, 72.0)",
            "user_objective": "safety_check",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "descriptive_synthesis" in data
    assert data["generation_mode"] in ("llm", "deterministic")
    assert "composite_safety_risk" in data
    assert data["composite_safety_risk"]["risk_category"] == "MODERATE"


# ==============================================================================
# 12. LLM Provider Precedence and Model Selection
# ==============================================================================

def test_llm_provider_precedence_and_model_selection(monkeypatch):
    """Verify provider precedence order: ORCA_LLM_PROVIDER > OPENAI_API_KEY > GEMINI_API_KEY."""
    from app.agents.llm_client import get_configured_llm_provider

    # Default: No keys configured -> None
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ORCA_LLM_PROVIDER", raising=False)
    assert get_configured_llm_provider() is None

    # OpenAI key set -> openai
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    assert get_configured_llm_provider() == "openai"

    # Both set without explicit preference -> openai takes precedence
    monkeypatch.setenv("GEMINI_API_KEY", "ai-gemini-key")
    assert get_configured_llm_provider() == "openai"

    # Both set with explicit ORCA_LLM_PROVIDER=gemini -> gemini
    monkeypatch.setenv("ORCA_LLM_PROVIDER", "gemini")
    assert get_configured_llm_provider() == "gemini"

    # Only Gemini key set -> gemini
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ORCA_LLM_PROVIDER", raising=False)
    assert get_configured_llm_provider() == "gemini"


# ==============================================================================
# 13. Malformed LLM Output and Non-JSON Handling
# ==============================================================================

@pytest.mark.asyncio
async def test_llm_malformed_json_fallback():
    """Verify call_json_llm falls back gracefully when model output is unparseable."""
    from app.agents.llm_client import call_json_llm

    # Scenario A: Non-JSON plain text
    with patch("app.agents.llm_client.call_chat_llm", AsyncMock(return_value=("Just a text reply", "llm"))):
        parsed, mode = await call_json_llm(system_prompt="sys", user_prompt="usr")
        assert parsed is None
        assert mode == "deterministic"

    # Scenario B: JSON array instead of dictionary
    with patch("app.agents.llm_client.call_chat_llm", AsyncMock(return_value=("[1, 2, 3]", "llm"))):
        parsed, mode = await call_json_llm(system_prompt="sys", user_prompt="usr")
        assert parsed is None
        assert mode == "deterministic"

    # Scenario C: Markdown-wrapped JSON is cleaned and parsed properly
    with patch("app.agents.llm_client.call_chat_llm", AsyncMock(return_value=("```json\n{\"intent\": \"weather\"}\n```", "llm"))):
        parsed, mode = await call_json_llm(system_prompt="sys", user_prompt="usr")
        assert parsed == {"intent": "weather"}
        assert mode == "llm"


# ==============================================================================
# 14. Secure Credential Management & Zero Secret Leaks
# ==============================================================================

def test_secure_credential_management_no_secret_leaks(monkeypatch):
    """Verify secrets and API keys are not exposed in error messages, schemas, or responses."""
    secret_token = "sk-super-secret-production-token-998877"
    monkeypatch.setenv("OPENAI_API_KEY", secret_token)

    # Call endpoint with invalid parameter to trigger error
    response = client.post(
        "/api/agents/orchestrator/analyze",
        json={"latitude": 999.0, "longitude": 72.0},  # Invalid out of bounds
    )
    assert response.status_code == 422
    response_body = response.text
    assert secret_token not in response_body
    assert "sk-" not in response_body

