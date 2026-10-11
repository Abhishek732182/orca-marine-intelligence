"""Orchestrator Agent API Route."""

from fastapi import APIRouter, HTTPException, status

from app.agents.orchestrator_agent import OrchestratorAgent
from app.schemas.agent_schemas import (
    OrchestratorAnalyzeRequest,
    OrchestratorAnalyzeResponse,
)

router = APIRouter(prefix="/agents/orchestrator", tags=["Orchestrator Agent"])
agent = OrchestratorAgent()


@router.post(
    "/analyze",
    response_model=OrchestratorAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Orchestrate Marine Mission Intelligence",
    description="ORCA Orchestrator Agent (Agent 6) coordinating specialist agents into a unified, evidence-grounded advisory.",
)
async def analyze_orchestrator(
    request: OrchestratorAnalyzeRequest,
) -> OrchestratorAnalyzeResponse:
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
            detail=f"Orchestrator agent error: {type(exc).__name__}: {str(exc)}",
        ) from exc
