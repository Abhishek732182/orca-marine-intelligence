
import httpx
from fastapi import APIRouter, HTTPException, Query

from app.data_sources.open_meteo_marine import (
    OpenMeteoMarineProvider,
)

router = APIRouter(prefix="/marine", tags=["Marine"])
provider = OpenMeteoMarineProvider()


@router.get("/wave-height")
async def get_wave_height(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
):
    try:
        records = await provider.fetch(
            latitude=latitude,
            longitude=longitude,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Marine data provider is temporarily unavailable.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "source": provider.provider_name,
        "count": len(records),
        "records": [
            record.model_dump(mode="json")
            for record in records
        ],
        "data_available": len(records) > 0,
    }
