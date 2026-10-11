"""Unit tests for independent Ocean Agent."""

from datetime import datetime, timezone
import pytest
import httpx
from unittest.mock import AsyncMock

from app.agents.ocean_agent import OceanAgent
from app.schemas.agent_schemas import OceanAnalyzeRequest
from app.schemas.evidence import EvidenceRecord


@pytest.fixture
def mock_marine_provider():
    provider = AsyncMock()
    provider.provider_name = "open-meteo-marine"
    provider.BASE_URL = "https://marine-api.open-meteo.com/v1/marine"
    return provider


@pytest.mark.asyncio
async def test_ocean_agent_valid_records(mock_marine_provider):
    now_utc = datetime.now(timezone.utc)
    mock_marine_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="ev-1",
            source="open-meteo-marine",
            source_record_id="2026-10-11T12:00:15:72",
            variable="wave_height",
            value=1.4,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc),
            retrieved_at=now_utc,
            status="valid",
            quality_flags=["forecast_data"],
        ),
        EvidenceRecord(
            evidence_id="ev-2",
            source="open-meteo-marine",
            source_record_id="2026-10-11T13:00:15:72",
            variable="wave_height",
            value=1.8,
            unit="m",
            latitude=15.0,
            longitude=72.0,
            observed_at=datetime(2026, 10, 11, 13, 0, tzinfo=timezone.utc),
            retrieved_at=now_utc,
            status="valid",
            quality_flags=["forecast_data"],
        ),
    ]

    agent = OceanAgent(provider=mock_marine_provider)
    request = OceanAnalyzeRequest(
        latitude=15.0,
        longitude=72.0,
        location_name="Offshore Goa",
        forecast_time_window_hours=24,
    )
    response = await agent.analyze(request)

    assert response.agent == "Ocean Agent"
    assert response.status == "success"
    assert response.observations["sample_count"] == 2
    assert response.observations["min_wave_height_m"] == 1.4
    assert response.observations["max_wave_height_m"] == 1.8
    assert response.observations["avg_wave_height_m"] == 1.6
    assert response.analysis["sea_state_code"] == 4  # Moderate (1.25m - 2.5m)
    assert response.analysis["sea_state_category"] == "Moderate"
    assert response.analysis["rule_standard"] == "WMO Code Table 3700 / Douglas Sea Scale"
    # Regression check: valid forecast records must not generate false timestamp warnings
    assert not any("observation_after_retrieval" in w for w in response.warnings)
    assert not any("observation_time_in_future" in w for w in response.warnings)



@pytest.mark.asyncio
async def test_ocean_agent_empty_evidence_on_land(mock_marine_provider):
    mock_marine_provider.fetch.return_value = []

    agent = OceanAgent(provider=mock_marine_provider)
    request = OceanAnalyzeRequest(
        latitude=21.15,
        longitude=79.09,
        location_name="Inland Nagpur",
    )
    response = await agent.analyze(request)

    assert response.status == "insufficient_evidence"
    assert response.observations["sample_count"] == 0
    assert response.analysis["sea_state_category"] == "UNKNOWN"
    assert "land or outside active numerical sea-grid" in response.analysis["summary"]
    assert len(response.warnings) >= 1


@pytest.mark.asyncio
async def test_ocean_agent_provider_failure(mock_marine_provider):
    mock_marine_provider.fetch.side_effect = httpx.TimeoutException("Upstream timeout")

    agent = OceanAgent(provider=mock_marine_provider)
    request = OceanAnalyzeRequest(latitude=15.0, longitude=72.0)
    response = await agent.analyze(request)

    assert response.status == "error"
    assert isinstance(response.error, str), f"Expected string error, got: {response.error!r}"
    assert "Upstream timeout" in response.error


@pytest.mark.asyncio
async def test_ocean_agent_invalid_coordinates(mock_marine_provider):
    agent = OceanAgent(provider=mock_marine_provider)
    with pytest.raises(Exception):
        OceanAnalyzeRequest(latitude=91.0, longitude=72.0)
