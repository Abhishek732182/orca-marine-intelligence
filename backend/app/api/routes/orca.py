"""ORCA Marine Intelligence Agent API route."""

import httpx
from fastapi import APIRouter, HTTPException, status

from app.agents.marine_graph import run_marine_workflow
from app.schemas.requests import OrcaAnalyzeRequest
from app.schemas.responses import OrcaAnalyzeResponse

router = APIRouter(prefix="/orca", tags=["ORCA Agent"])


@router.post(
    "/analyze",
    response_model=OrcaAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Run ORCA Marine Intelligence Agent Analysis",
    description=(
        "Executes the single LangGraph ORCA Marine Intelligence Agent to fetch, "
        "normalize, validate, analyze wave conditions using WMO Code Table 3700, "
        "and generate an evidence-grounded marine advisory."
    ),
)
async def analyze_marine_conditions(
    request: OrcaAnalyzeRequest,
) -> OrcaAnalyzeResponse:
    """Execute ORCA Marine Intelligence Agent workflow."""
    try:
        result = await run_marine_workflow(
            latitude=request.latitude,
            longitude=request.longitude,
            location_name=request.location_name,
            forecast_time_window_hours=request.forecast_time_window_hours,
        )

        structured_output = result.get("structured_output")
        if not structured_output:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Workflow failed to generate structured output.",
            )

        return OrcaAnalyzeResponse.model_validate(structured_output)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Marine data provider timed out: {str(exc)}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Marine data provider error: {str(exc)}",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent workflow error: {type(exc).__name__}: {str(exc)}",
        ) from exc
