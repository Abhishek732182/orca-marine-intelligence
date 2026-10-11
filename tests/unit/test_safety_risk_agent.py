"""Unit tests for independent Safety/Risk Agent."""

from datetime import datetime, timedelta, timezone
import pytest
import httpx
from unittest.mock import AsyncMock

from app.agents.safety_risk_agent import SafetyRiskAgent
from app.schemas.agent_schemas import SafetyRiskAnalyzeRequest
from app.schemas.evidence import EvidenceRecord


@pytest.fixture
def mock_providers():
    marine_prov = AsyncMock()
    marine_prov.provider_name = "open-meteo-marine"

    weather_prov = AsyncMock()
    weather_prov.provider_name = "open-meteo-weather"

    return marine_prov, weather_prov


@pytest.mark.asyncio
async def test_safety_risk_agent_manual_inputs(mock_providers):
    marine_prov, weather_prov = mock_providers
    agent = SafetyRiskAgent(marine_provider=marine_prov, weather_provider=weather_prov)

    # Moderate conditions for small craft
    request = SafetyRiskAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        vessel_type="small_craft",
        wave_height_m=1.6,
        wind_speed_knots=18.0,
        precipitation_mm=1.0,
    )
    response = await agent.analyze(request)

    assert response.agent == "Safety/Risk Agent"
    assert response.status == "success"
    assert response.analysis["risk_category"] == "MODERATE"
    assert response.observations["data_completeness"] == "COMPLETE"
    assert "Manual wave observation input" in response.data_source["sources_used"]
    assert "DECISION SUPPORT ONLY" in response.analysis["legal_notice"]


@pytest.mark.asyncio
async def test_safety_risk_agent_critical_conditions(mock_providers):
    marine_prov, weather_prov = mock_providers
    agent = SafetyRiskAgent(marine_provider=marine_prov, weather_provider=weather_prov)

    request = SafetyRiskAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        vessel_type="small_craft",
        wave_height_m=3.8,  # > 3.0 m is critical for small craft
        wind_speed_knots=38.0,  # > 34 kts is gale force / critical
    )
    response = await agent.analyze(request)

    assert response.status == "success"
    assert response.analysis["risk_category"] == "CRITICAL"
    assert any("Critical wave hazard" in r for r in response.analysis["risk_reasons"])
    assert any("Gale force winds" in r for r in response.analysis["risk_reasons"])


@pytest.mark.asyncio
async def test_safety_risk_agent_missing_evidence_not_safe(mock_providers):
    marine_prov, weather_prov = mock_providers
    marine_prov.fetch.return_value = []
    weather_prov.fetch_weather.return_value = {"current_weather": {}, "hourly": {}}

    agent = SafetyRiskAgent(marine_provider=marine_prov, weather_provider=weather_prov)
    request = SafetyRiskAnalyzeRequest(latitude=21.15, longitude=79.09)
    response = await agent.analyze(request)

    # Must NOT classify missing data as safe!
    assert response.status == "insufficient_evidence"
    assert response.analysis["risk_category"] == "UNKNOWN / INSUFFICIENT EVIDENCE"
    assert "DO NOT PRESUME SAFE" in response.analysis["recommendations"][0]
    assert "Missing evidence is strictly NOT classified as safe" in response.warnings[1]


@pytest.mark.asyncio
async def test_safety_risk_agent_live_provider_fetch(mock_providers):
    marine_prov, weather_prov = mock_providers
    now_utc = datetime.now(timezone.utc)
    marine_prov.fetch.return_value = [
        EvidenceRecord(
            evidence_id="ev-10",
            source="open-meteo-marine",
            source_record_id="rec-10",
            variable="wave_height",
            value=0.8,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        )
    ]
    weather_prov.fetch_weather.return_value = {
        "current_weather": {"windspeed": 15.0, "time": "2026-10-11T12:00"},
        "hourly": {"precipitation": [0.0]},
    }

    agent = SafetyRiskAgent(marine_provider=marine_prov, weather_provider=weather_prov)
    request = SafetyRiskAnalyzeRequest(latitude=15.0, longitude=72.0, vessel_type="trawler")
    response = await agent.analyze(request)

    assert response.status == "success"
    assert response.observations["wave_height_m"] == 0.8
    assert response.analysis["risk_category"] == "LOW"


@pytest.mark.asyncio
async def test_safety_risk_agent_missing_wave_evidence_cannot_be_low(mock_providers):
    """When wave data is missing, agent must NOT classify risk as LOW or return favorable recommendations."""
    marine_prov, weather_prov = mock_providers
    marine_prov.fetch.return_value = []
    weather_prov.fetch_weather.return_value = {
        "current_weather": {"windspeed": 10.0, "time": "2026-10-11T12:00"},  # 5.4 knots (calm)
        "hourly": {"precipitation": [0.0]},
    }

    agent = SafetyRiskAgent(marine_provider=marine_prov, weather_provider=weather_prov)
    request = SafetyRiskAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        vessel_type="small_craft",
    )
    response = await agent.analyze(request)

    assert response.status == "insufficient_evidence"
    assert response.analysis["risk_category"] == "UNKNOWN / INSUFFICIENT EVIDENCE"
    assert not any("FAVORABLE" in r for r in response.analysis["recommendations"])
    assert any("EVIDENCE INCOMPLETE" in r for r in response.analysis["recommendations"])


@pytest.mark.asyncio
async def test_safety_risk_agent_missing_wind_evidence_cannot_be_low(mock_providers):
    """When wind data is missing, agent must NOT classify risk as LOW or return favorable recommendations."""
    marine_prov, weather_prov = mock_providers
    now_utc = datetime.now(timezone.utc)
    marine_prov.fetch.return_value = [
        EvidenceRecord(
            evidence_id="ev-calm",
            source="open-meteo-marine",
            source_record_id="rec-calm",
            variable="wave_height",
            value=0.4,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        )
    ]
    weather_prov.fetch_weather.return_value = {}  # Empty weather

    agent = SafetyRiskAgent(marine_provider=marine_prov, weather_provider=weather_prov)
    request = SafetyRiskAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        vessel_type="small_craft",
    )
    response = await agent.analyze(request)

    assert response.status == "insufficient_evidence"
    assert response.analysis["risk_category"] == "UNKNOWN / INSUFFICIENT EVIDENCE"
    assert not any("FAVORABLE" in r for r in response.analysis["recommendations"])


@pytest.mark.asyncio
async def test_safety_risk_agent_hazardous_waves_high_and_critical(mock_providers):
    """Verify hazardous wave thresholds for small craft."""
    marine_prov, weather_prov = mock_providers
    agent = SafetyRiskAgent(marine_provider=marine_prov, weather_provider=weather_prov)

    # 1. High risk: 2.2m wave
    res_high = await agent.analyze(SafetyRiskAnalyzeRequest(
        latitude=15.0, longitude=72.0, vessel_type="small_craft", wave_height_m=2.2, wind_speed_knots=10.0
    ))
    assert res_high.status == "success"
    assert res_high.analysis["risk_category"] == "HIGH"
    assert any("HIGH RISK" in r for r in res_high.analysis["recommendations"])

    # 2. Critical risk: 3.2m wave
    res_crit = await agent.analyze(SafetyRiskAnalyzeRequest(
        latitude=15.0, longitude=72.0, vessel_type="small_craft", wave_height_m=3.2, wind_speed_knots=10.0
    ))
    assert res_crit.status == "success"
    assert res_crit.analysis["risk_category"] == "CRITICAL"
    assert any("DANGER" in r for r in res_crit.analysis["recommendations"])


@pytest.mark.asyncio
async def test_safety_risk_agent_high_wind_hazards(mock_providers):
    """Verify high wind and gale force risk escalation."""
    marine_prov, weather_prov = mock_providers
    agent = SafetyRiskAgent(marine_provider=marine_prov, weather_provider=weather_prov)

    # 1. High risk: 26.0 knots wind
    res_high = await agent.analyze(SafetyRiskAnalyzeRequest(
        latitude=15.0, longitude=72.0, vessel_type="small_craft", wave_height_m=1.0, wind_speed_knots=26.0
    ))
    assert res_high.analysis["risk_category"] == "HIGH"

    # 2. Critical risk: 36.0 knots wind (Gale)
    res_crit = await agent.analyze(SafetyRiskAnalyzeRequest(
        latitude=15.0, longitude=72.0, vessel_type="small_craft", wave_height_m=1.0, wind_speed_knots=36.0
    ))
    assert res_crit.analysis["risk_category"] == "CRITICAL"


@pytest.mark.asyncio
async def test_safety_risk_agent_stale_timestamps(mock_providers):
    """Verify stale observation timestamps are flagged and do not return LOW risk."""
    marine_prov, weather_prov = mock_providers
    old_time = datetime.now(timezone.utc) - timedelta(hours=48)
    marine_prov.fetch.return_value = [
        EvidenceRecord(
            evidence_id="ev-stale",
            source="open-meteo-marine",
            source_record_id="rec-stale",
            variable="wave_height",
            value=0.5,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=old_time,
            retrieved_at=old_time,
            status="stale",
        )
    ]
    weather_prov.fetch_weather.return_value = {
        "current_weather": {"windspeed": 10.0, "time": "2026-10-09T12:00"},
        "hourly": {"precipitation": [0.0]},
    }

    agent = SafetyRiskAgent(marine_provider=marine_prov, weather_provider=weather_prov)
    response = await agent.analyze(SafetyRiskAnalyzeRequest(
        latitude=15.0, longitude=72.0, vessel_type="small_craft"
    ))

    assert response.status == "insufficient_evidence"
    assert response.analysis["risk_category"] != "LOW"
    assert not any("FAVORABLE" in r for r in response.analysis["recommendations"])
    assert any("stale" in w.lower() for w in response.warnings)


@pytest.mark.asyncio
async def test_safety_risk_agent_provider_failure_returns_error_and_not_safe(mock_providers):
    """Verify that upstream network/provider errors return error/insufficient status and not safe."""
    marine_prov, weather_prov = mock_providers
    marine_prov.fetch.side_effect = httpx.ConnectError("Connection refused by marine provider")
    weather_prov.fetch_weather.side_effect = httpx.ConnectError("Connection refused by weather provider")

    agent = SafetyRiskAgent(marine_provider=marine_prov, weather_provider=weather_prov)
    response = await agent.analyze(SafetyRiskAnalyzeRequest(
        latitude=15.0, longitude=72.0, vessel_type="small_craft"
    ))

    assert response.status in ("error", "insufficient_evidence")
    assert response.analysis["risk_category"] == "UNKNOWN / INSUFFICIENT EVIDENCE"
    assert not any("FAVORABLE" in r for r in response.analysis["recommendations"])
    assert response.error is not None
    assert "Connection refused" in response.error
