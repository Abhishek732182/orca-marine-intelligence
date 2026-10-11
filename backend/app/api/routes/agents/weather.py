"""Weather Agent API Route."""

from fastapi import APIRouter, HTTPException, status

from app.agents.weather_agent import WeatherAgent
from app.schemas.agent_schemas import (
    WeatherAnalyzeRequest,
    WeatherAnalyzeResponse,
)

router = APIRouter(prefix="/agents/weather", tags=["Weather Agent"])
agent = WeatherAgent()


@router.post(
    "/analyze",
    response_model=WeatherAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze Weather Conditions",
    description="Independent Weather Agent endpoint retrieving current and forecast atmospheric conditions.",
)
async def analyze_weather(request: WeatherAnalyzeRequest) -> WeatherAnalyzeResponse:
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
            detail=f"Weather agent error: {type(exc).__name__}: {str(exc)}",
        ) from exc
