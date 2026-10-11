"""Fishing Zone Agent API Route."""

from fastapi import APIRouter, HTTPException, status

from app.agents.fishing_zone_agent import FishingZoneAgent
from app.schemas.agent_schemas import (
    FishingZoneAnalyzeRequest,
    FishingZoneAnalyzeResponse,
)

router = APIRouter(prefix="/agents/fishing-zone", tags=["Fishing Zone Agent"])
agent = FishingZoneAgent()


@router.post(
    "/analyze",
    response_model=FishingZoneAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze Fishing Zone & Fisheries Suitability",
    description="Independent Fishing Zone Agent endpoint evaluating marine conditions and operational vessel feasibility.",
)
async def analyze_fishing_zone(
    request: FishingZoneAnalyzeRequest,
) -> FishingZoneAnalyzeResponse:
    try:
        response = await agent.analyze(request)
        return response
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fishing zone agent error: {type(exc).__name__}: {str(exc)}",
        ) from exc
