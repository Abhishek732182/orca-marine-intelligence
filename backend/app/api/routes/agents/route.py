"""Route Agent API Route."""

from fastapi import APIRouter, HTTPException, status

from app.agents.route_agent import RouteAgent
from app.schemas.agent_schemas import (
    RouteAnalyzeRequest,
    RouteAnalyzeResponse,
)

router = APIRouter(prefix="/agents/route", tags=["Route Agent"])
agent = RouteAgent()


@router.post(
    "/analyze",
    response_model=RouteAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze Maritime Route & Geodesics",
    description="Independent Route Agent endpoint calculating geodesic distances, bearings, waypoints, and transit times.",
)
async def analyze_route(request: RouteAnalyzeRequest) -> RouteAnalyzeResponse:
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
            detail=f"Route agent error: {type(exc).__name__}: {str(exc)}",
        ) from exc
