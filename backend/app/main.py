
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router

app = FastAPI(
    title="ORCA Marine Intelligence API",
    description="Evidence-based marine decision support.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# API routes: /api/health and /api/marine/...
app.include_router(api_router, prefix="/api")

# Keep the original health URL working for backward compatibility.
app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "ORCA API is running"}
