import pytest

from app.agents import marine_graph as workflow


@pytest.mark.asyncio
async def test_workflow_returns_insufficient_evidence_when_provider_fails(
    monkeypatch,
):
    async def fake_fetch(*, latitude, longitude):
        raise RuntimeError("simulated provider failure")

    monkeypatch.setattr(workflow.provider, "fetch", fake_fetch)

    result = await workflow.run_marine_workflow(
        latitude=15.0,
        longitude=72.0,
    )

    assert result.get("evidence") == []
    assert result.get("result_status") == "insufficient_evidence"
    assert result.get("issues")


@pytest.mark.asyncio
async def test_workflow_rejects_invalid_coordinates():
    with pytest.raises(ValueError, match="latitude"):
        await workflow.run_marine_workflow(
            latitude=100.0,
            longitude=72.0,
        )

    with pytest.raises(ValueError, match="longitude"):
        await workflow.run_marine_workflow(
            latitude=15.0,
            longitude=200.0,
        )
