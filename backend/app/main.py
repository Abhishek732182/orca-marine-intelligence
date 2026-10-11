
import os
import sys
from pathlib import Path

# Ensure backend root directory is in sys.path for direct imports
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from app.api.router import api_router
from app.api.routes.health import router as health_router

app = FastAPI(
    title="ORCA Marine Intelligence API",
    description="Evidence-based marine decision support.",
    version="0.1.0",
)

# Configured CORS origins (local React development and configured production frontend)
cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]
configured_origin = os.getenv("FRONTEND_ORIGIN")
if configured_origin and configured_origin not in cors_origins:
    cors_origins.append(configured_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# API routes mounted at /api prefix (/api/health, /api/marine, /api/orca, /api/agents)
app.include_router(api_router, prefix="/api")

# Keep the original /health URL working for backward compatibility
app.include_router(health_router)


@app.get("/")
async def root():
    return {"message": "ORCA API is running"}



