"""Ocean Agent API Route."""

from fastapi import APIRouter, HTTPException, status

from app.agents.ocean_agent import OceanAgent
from app.schemas.agent_schemas import (
    OceanAnalyzeRequest,
    OceanAnalyzeResponse,
)

router = APIRouter(prefix="/agents/ocean", tags=["Ocean Agent"])
agent = OceanAgent()


@router.post(
    "/analyze",
    response_model=OceanAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze Ocean & Wave Conditions",
    description="Independent Ocean Agent endpoint calculating wave metrics and WMO Code Table 3700 sea states.",
)
async def analyze_ocean(request: OceanAnalyzeRequest) -> OceanAnalyzeResponse:
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
            detail=f"Ocean agent error: {type(exc).__name__}: {str(exc)}",
        ) from exc
