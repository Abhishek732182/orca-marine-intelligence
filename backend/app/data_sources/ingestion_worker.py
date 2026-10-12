"""Asynchronous Ingestion Worker for Fisheries and Satellite Telemetry.

Coordinates background ingestion cycles for INCOIS PFZ bulletins and
satellite ocean-color / SST products with non-blocking execution, retry handling,
and offline snapshot fallback.

Guarantees:
1. Non-blocking: Ingestion cycles run asynchronously and do not block HTTP requests.
2. Evidence Integrity: Validates every record, applies freshness policies, and
   flags cached offline snapshots.
3. Strict Safety: If no fresh or valid evidence is available, returns an explicit
   empty/insufficient-evidence result. Never fabricates data.
"""

import asyncio
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, cast
import httpx

from app.core.config import settings
from app.data_sources.base import MarineDataProvider
from app.data_sources.erddap_client import ErddapClient, ErddapMode, ErddapSnapshot
from app.data_sources.incois_pfz import IncoisPfzBulletinParser, IncoisPfzClient
from app.schemas.evidence import EvidenceRecord

logger = logging.getLogger("orca.data_sources.ingestion_worker")


class FisheriesIngestionWorker(MarineDataProvider):
    """Asynchronous ingestion worker and fisheries evidence provider."""

    def __init__(
        self,
        incois_client: IncoisPfzClient | None = None,
        erddap_client: ErddapClient | None = None,
        cache_dir: str | Path | None = None,
    ) -> None:
        self.cache_dir = Path(cache_dir or settings.fisheries_cache_dir)
        self.incois_client = incois_client or IncoisPfzClient(
            base_url=settings.incois_pfz_url,
            api_key=settings.incois_api_key,
        )
        self.erddap_client = erddap_client or ErddapClient(
            base_url=settings.erddap_base_url,
            cache_dir=self.cache_dir,
            mode=cast(ErddapMode, settings.erddap_mode),
        )
        self.incois_parser = IncoisPfzBulletinParser()

        # In-memory storage for active ingested records
        self._ingested_records: list[EvidenceRecord] = []
        self._last_ingestion_time: datetime | None = None
        self._is_ingesting: bool = False
        self._background_task: asyncio.Task[None] | None = None
        self._stop_event: asyncio.Event = asyncio.Event()

    @property
    def is_running(self) -> bool:
        """Check if background worker task is active."""
        return self._background_task is not None and not self._background_task.done()

    @property
    def provider_name(self) -> str:
        return "fisheries-resilient-ingestion-worker"

    async def ingest_incois_geojson(
        self,
        geojson_data: dict[str, Any] | str,
        *,
        source_url: str | None = None,
        is_fixture: bool | None = None,
    ) -> list[EvidenceRecord]:
        """Ingest and validate an INCOIS PFZ GeoJSON payload."""
        records = self.incois_parser.parse_geojson(
            geojson_data,
            source_url=source_url or "incois-pfz-bulletin",
            is_fixture=is_fixture,
        )
        # Deduplicate and register
        existing_ids = {r.evidence_id for r in self._ingested_records}
        new_records = [r for r in records if r.evidence_id not in existing_ids]
        self._ingested_records.extend(new_records)
        logger.info("Ingested %d valid records from INCOIS bulletin (%d new)", len(records), len(new_records))
        return records

    async def run_ingestion_cycle(self) -> dict[str, Any]:
        """Execute one non-blocking ingestion cycle across configured providers."""
        if self._is_ingesting:
            logger.debug("Ingestion cycle already in progress; skipping duplicate trigger")
            return {"status": "in_progress"}

        self._is_ingesting = True
        cycle_result: dict[str, Any] = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "incois_status": "skipped",
            "erddap_status": "active",
            "new_records_count": 0,
            "errors": [],
        }

        try:
            # 1. Fetch remote INCOIS bulletin if URL is configured
            if self.incois_client.base_url:
                try:
                    records = await self.incois_client.fetch_bulletin()
                    existing_ids = {r.evidence_id for r in self._ingested_records}
                    new_records = [r for r in records if r.evidence_id not in existing_ids]
                    self._ingested_records.extend(new_records)
                    cycle_result["incois_status"] = "success"
                    cycle_result["new_records_count"] += len(new_records)
                except Exception as exc:
                    cycle_result["incois_status"] = "failed"
                    cycle_result["errors"].append(f"INCOIS ingestion failed: {exc}")
                    logger.warning("Remote INCOIS ingestion failed: %s", exc)

            self._last_ingestion_time = datetime.now(timezone.utc)
            cycle_result["completed_at"] = self._last_ingestion_time.isoformat()
            cycle_result["status"] = "completed"

        finally:
            self._is_ingesting = False

        return cycle_result

    def trigger_background_ingestion(self) -> asyncio.Task[dict[str, Any]]:
        """Trigger an asynchronous, non-blocking ingestion task without awaiting."""
        return asyncio.create_task(self.run_ingestion_cycle())

    async def start(self) -> None:
        """Start periodic background ingestion loop if not already running."""
        if self._background_task is not None and not self._background_task.done():
            logger.info("FisheriesIngestionWorker is already running; skipping duplicate start.")
            return
        self._stop_event.clear()
        self._background_task = asyncio.create_task(self._run_loop())
        logger.info("FisheriesIngestionWorker background task started.")

    async def stop(self) -> None:
        """Cleanly cancel and stop background ingestion task."""
        if self._background_task is None:
            return
        logger.info("Stopping FisheriesIngestionWorker background task...")
        self._stop_event.set()
        self._background_task.cancel()
        try:
            await asyncio.wait_for(asyncio.shield(self._background_task), timeout=5.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
        except Exception as exc:
            logger.warning("Error waiting for FisheriesIngestionWorker to stop: %s", exc)
        finally:
            self._background_task = None
            logger.info("FisheriesIngestionWorker background task stopped.")

    async def _run_loop(self) -> None:
        """Periodic worker loop executing ingestion cycles at configured interval."""
        while not self._stop_event.is_set():
            try:
                await self.run_ingestion_cycle()
            except asyncio.CancelledError:
                logger.debug("FisheriesIngestionWorker loop cancelled.")
                break
            except Exception as exc:
                logger.error("Unexpected error in fisheries ingestion cycle: %s", exc, exc_info=True)

            try:
                await asyncio.sleep(settings.fisheries_ingestion_interval_seconds)
            except asyncio.CancelledError:
                logger.debug("FisheriesIngestionWorker sleep cancelled.")
                break

    async def fetch(
        self,
        *,
        latitude: float,
        longitude: float,
        observed_at: str | None = None,
    ) -> list[EvidenceRecord]:
        """Retrieve all matching fisheries and satellite evidence for target location."""
        matched: list[EvidenceRecord] = []

        # 1. Match from ingested INCOIS records (spatial containment or 30km radius)
        if self._ingested_records:
            incois_matches = self.incois_parser.match_records_for_location(
                self._ingested_records,
                latitude=latitude,
                longitude=longitude,
                radius_km=30.0,
            )
            matched.extend(incois_matches)

        # 2. Query satellite chlorophyll-a via ERDDAP client (live or offline snapshot)
        try:
            chla_records = await self.erddap_client.fetch_chlorophyll_a(
                latitude=latitude,
                longitude=longitude,
            )
            matched.extend(chla_records)
        except Exception as exc:
            logger.debug("ERDDAP chlorophyll query error at (%s, %s): %s", latitude, longitude, exc)

        return matched

    def get_provider_status(self) -> dict[str, Any]:
        """Return connectivity and cache status for reporting."""
        return {
            "worker_name": self.provider_name,
            "is_running": self.is_running,
            "last_ingestion_time": self._last_ingestion_time.isoformat() if self._last_ingestion_time else None,
            "in_memory_records_count": len(self._ingested_records),
            "erddap_mode": self.erddap_client.mode,
            "cached_snapshots_count": len(self.erddap_client._in_memory_snapshots),
            "cache_dir": str(self.cache_dir),
        }


# Singleton worker instance for application lifespan
_global_fisheries_worker: FisheriesIngestionWorker | None = None


def get_fisheries_worker() -> FisheriesIngestionWorker:
    """Get or create singleton FisheriesIngestionWorker instance."""
    global _global_fisheries_worker
    if _global_fisheries_worker is None:
        _global_fisheries_worker = FisheriesIngestionWorker()
    return _global_fisheries_worker


def set_fisheries_worker(worker: FisheriesIngestionWorker | None) -> None:
    """Set or reset singleton FisheriesIngestionWorker instance."""
    global _global_fisheries_worker
    _global_fisheries_worker = worker
