"""Five Independent ORCA Agents routes."""

from fastapi import APIRouter

from app.api.routes.agents.weather import router as weather_router
from app.api.routes.agents.ocean import router as ocean_router
from app.api.routes.agents.fishing_zone import router as fishing_zone_router
from app.api.routes.agents.route import router as route_router
from app.api.routes.agents.safety_risk import router as safety_risk_router
from app.api.routes.agents.orchestrator import router as orchestrator_router
from app.api.routes.agents.assistant import router as assistant_router

agents_router = APIRouter()
agents_router.include_router(weather_router)
agents_router.include_router(ocean_router)
agents_router.include_router(fishing_zone_router)
agents_router.include_router(route_router)
agents_router.include_router(safety_risk_router)
agents_router.include_router(orchestrator_router)
agents_router.include_router(assistant_router)

__all__ = [
    "agents_router",
    "weather_router",
    "ocean_router",
    "fishing_zone_router",
    "route_router",
    "safety_risk_router",
    "orchestrator_router",
    "assistant_router",
]

