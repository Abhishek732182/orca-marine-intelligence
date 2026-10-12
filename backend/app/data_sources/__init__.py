"""Data sources package for ORCA Marine Intelligence."""

from app.data_sources.base import MarineDataProvider
from app.data_sources.erddap_client import ErddapClient, ErddapSnapshot
from app.data_sources.incois_pfz import IncoisPfzBulletinParser, IncoisPfzClient
from app.data_sources.ingestion_worker import (
    FisheriesIngestionWorker,
    get_fisheries_worker,
    set_fisheries_worker,
)
from app.data_sources.open_meteo_marine import OpenMeteoMarineProvider
from app.data_sources.open_meteo_weather import OpenMeteoWeatherProvider

__all__ = [
    "MarineDataProvider",
    "OpenMeteoMarineProvider",
    "OpenMeteoWeatherProvider",
    "IncoisPfzBulletinParser",
    "IncoisPfzClient",
    "ErddapClient",
    "ErddapSnapshot",
    "FisheriesIngestionWorker",
    "get_fisheries_worker",
    "set_fisheries_worker",
]
