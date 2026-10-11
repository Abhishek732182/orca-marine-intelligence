
from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.marine import router as marine_router
from app.api.routes.orca import router as orca_router

api_router = APIRouter()

# Health check endpoint
api_router.include_router(health_router)

# Marine forecast endpoints
api_router.include_router(marine_router)

# ORCA Marine Intelligence Agent endpoint
api_router.include_router(orca_router)
