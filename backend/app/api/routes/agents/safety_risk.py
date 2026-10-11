"""Safety/Risk Agent API Route."""

from fastapi import APIRouter, HTTPException, status

from app.agents.safety_risk_agent import SafetyRiskAgent
from app.schemas.agent_schemas import (
    SafetyRiskAnalyzeRequest,
    SafetyRiskAnalyzeResponse,
)

router = APIRouter(prefix="/agents/safety-risk", tags=["Safety/Risk Agent"])
agent = SafetyRiskAgent()


@router.post(
    "/analyze",
    response_model=SafetyRiskAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze Marine Safety and Hazard Risk",
    description="Independent Safety/Risk Agent assessing wave, wind, and vessel operational hazard categories.",
)
async def analyze_safety_risk(
    request: SafetyRiskAnalyzeRequest,
) -> SafetyRiskAnalyzeResponse:
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
            detail=f"Safety/Risk agent error: {type(exc).__name__}: {str(exc)}",
        ) from exc
