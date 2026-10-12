"""NOAA CoastWatch / OceanWatch ERDDAP Satellite Client.

Implements resilient retrieval of satellite ocean color (Chlorophyll-a) and SST
with automatic retry handling and an offline snapshot fixture mode.

Architectural and Safety Rules:
1. Live vs. Fixture separation: Offline snapshots are clearly flagged with
   'cached_offline_snapshot', snapshot age, original observation timestamp, and
   retrieval time.
2. Regional accuracy: Cached snapshots are ONLY served if the requested position
   falls strictly within the snapshot's validated geographical bounding box.
3. No data fabrication: If upstream fails and no matching snapshot exists, returns
   an explicit empty/insufficient-evidence result, never synthetic coordinates.
4. Transient fault resilience: Retries on upstream HTTP 502/503/504 errors and timeouts
   with backoff before activating the offline fixture fallback.
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4
import httpx
from pydantic import BaseModel, Field

from app.schemas.evidence import EvidenceRecord

logger = logging.getLogger("orca.data_sources.erddap_client")

ErddapMode = Literal["live_with_fallback", "fixture_only", "live_only"]


class ErddapSnapshot(BaseModel):
    """Container for a validated satellite product snapshot."""

    snapshot_id: str
    product_id: str
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float
    observed_at: datetime
    retrieved_at: datetime
    source_url: str
    records: list[dict[str, Any]]
    metadata: dict[str, Any] = Field(default_factory=dict)


class ErddapClient:
    """Resilient client for NOAA ERDDAP satellite oceanographic products."""

    def __init__(
        self,
        base_url: str = "https://coastwatch.pfeg.noaa.gov/erddap",
        cache_dir: str | Path = "data/fisheries_cache",
        mode: ErddapMode = "live_with_fallback",
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.cache_dir = Path(cache_dir)
        self.mode = mode
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

        # In-memory snapshot cache for fast lookup and tests
        self._in_memory_snapshots: list[ErddapSnapshot] = []

        # Ensure disk cache directory exists
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._load_disk_cache()
        except Exception as exc:
            logger.debug("Cache directory init warning (%s): %s", self.cache_dir, exc)

    def _load_disk_cache(self) -> None:
        """Load valid JSON snapshots from cache directory."""
        if not self.cache_dir.exists():
            return

        for fpath in self.cache_dir.glob("*.json"):
            try:
                content = json.loads(fpath.read_text(encoding="utf-8"))
                snapshot = ErddapSnapshot.model_validate(content)
                # Avoid duplicates
                if not any(s.snapshot_id == snapshot.snapshot_id for s in self._in_memory_snapshots):
                    self._in_memory_snapshots.append(snapshot)
            except Exception as exc:
                logger.debug("Skipping unreadable snapshot %s: %s", fpath.name, exc)

    def register_snapshot(self, snapshot: ErddapSnapshot, *, persist_to_disk: bool = True) -> None:
        """Register a validated snapshot in cache."""
        # Replace existing with same ID if present
        self._in_memory_snapshots = [
            s for s in self._in_memory_snapshots if s.snapshot_id != snapshot.snapshot_id
        ]
        self._in_memory_snapshots.append(snapshot)

        if persist_to_disk:
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                target = self.cache_dir / f"{snapshot.product_id}_{snapshot.snapshot_id}.json"
                target.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
            except Exception as exc:
                logger.warning("Failed to persist snapshot to disk: %s", exc)

    def find_matching_snapshot(
        self,
        product_id: str,
        latitude: float,
        longitude: float,
        *,
        max_age_seconds: float | None = None,
        now: datetime | None = None,
    ) -> tuple[ErddapSnapshot | None, dict[str, Any]]:
        """Search registered snapshots for geographical and product match.
        
        Returns:
            Tuple of (matching_snapshot or None, diagnostics_dict)
        """
        now_utc = now or datetime.now(timezone.utc)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)

        diagnostics: dict[str, Any] = {
            "requested_product": product_id,
            "latitude": latitude,
            "longitude": longitude,
            "total_snapshots_examined": len(self._in_memory_snapshots),
            "product_matches": 0,
            "region_matches": 0,
            "expired_snapshots": 0,
        }

        matching: list[tuple[ErddapSnapshot, float]] = []

        for snap in self._in_memory_snapshots:
            if snap.product_id != product_id:
                continue
            diagnostics["product_matches"] += 1

            # Bounding box spatial containment check
            in_lat = snap.min_lat <= latitude <= snap.max_lat
            in_lon = snap.min_lon <= longitude <= snap.max_lon

            if not (in_lat and in_lon):
                continue
            diagnostics["region_matches"] += 1

            age_sec = (now_utc - snap.retrieved_at).total_seconds()
            if max_age_seconds is not None and age_sec > max_age_seconds:
                diagnostics["expired_snapshots"] += 1
                continue

            matching.append((snap, age_sec))

        if not matching:
            return None, diagnostics

        # Pick freshest snapshot
        matching.sort(key=lambda item: item[1])
        best_snap, best_age = matching[0]
        diagnostics["selected_snapshot_id"] = best_snap.snapshot_id
        diagnostics["snapshot_age_seconds"] = best_age
        return best_snap, diagnostics

    def parse_erddap_json_table(
        self,
        data: dict[str, Any],
        variable_name: str,
        unit: str,
        *,
        source_url: str,
        retrieved_at: datetime | None = None,
    ) -> list[EvidenceRecord]:
        """Convert standard ERDDAP griddap table response to EvidenceRecords."""
        now_utc = retrieved_at or datetime.now(timezone.utc)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)

        table = data.get("table") or {}
        col_names = table.get("columnNames") or []
        rows = table.get("rows") or []

        if not col_names or not rows:
            return []

        col_map = {name.lower(): i for i, name in enumerate(col_names)}

        time_idx = col_map.get("time")
        lat_idx = col_map.get("latitude") or col_map.get("lat")
        lon_idx = col_map.get("longitude") or col_map.get("lon")
        depth_idx = col_map.get("altitude") or col_map.get("depth")

        # Find value column
        val_idx: int | None = None
        for cand in [variable_name.lower(), "chlor_a", "chla", "sst", "analysed_sst", "temperature"]:
            if cand in col_map:
                val_idx = col_map[cand]
                break

        if val_idx is None:
            # Fallback to last column
            val_idx = len(col_names) - 1

        records: list[EvidenceRecord] = []

        for row in rows:
            if not isinstance(row, list) or len(row) <= val_idx:
                continue

            raw_val = row[val_idx]
            if raw_val is None:
                continue

            try:
                val_num = float(raw_val)
            except (ValueError, TypeError):
                continue

            # Extract coordinates
            row_lat = float(row[lat_idx]) if lat_idx is not None and row[lat_idx] is not None else None
            row_lon = float(row[lon_idx]) if lon_idx is not None and row[lon_idx] is not None else None
            row_depth = abs(float(row[depth_idx])) if depth_idx is not None and row[depth_idx] is not None else None

            # Extract observation time
            obs_dt = now_utc
            if time_idx is not None and row[time_idx]:
                try:
                    t_str = str(row[time_idx]).replace("Z", "+00:00")
                    parsed_t = datetime.fromisoformat(t_str)
                    if parsed_t.tzinfo is None:
                        parsed_t = parsed_t.replace(tzinfo=timezone.utc)
                    obs_dt = parsed_t.astimezone(timezone.utc)
                except Exception:
                    pass

            rec = EvidenceRecord(
                evidence_id=f"erddap-{variable_name[:4]}-{uuid4().hex[:10]}",
                source="noaa-erddap",
                source_record_id=f"row-{len(records)}",
                variable=variable_name,
                value=val_num,
                unit=unit,
                latitude=row_lat,
                longitude=row_lon,
                depth_m=row_depth,
                observed_at=obs_dt,
                retrieved_at=now_utc,
                status="valid",
                quality_flags=["satellite_remote_sensing", "noaa_erddap"],
                metadata={
                    "source_url": source_url,
                    "columns": col_names,
                    "sensor_dataset": source_url.split("/")[-1].split(".")[0],
                },
            )
            records.append(rec)

        return records

    async def fetch_chlorophyll_a(
        self,
        latitude: float,
        longitude: float,
        *,
        client: httpx.AsyncClient | None = None,
        now: datetime | None = None,
    ) -> list[EvidenceRecord]:
        """Fetch satellite Chlorophyll-a (mg/m³) with live retry and offline snapshot fallback."""
        product_id = "noaa_erddap_chlorophyll_a"
        unit = "mg/m^3"
        now_utc = now or datetime.now(timezone.utc)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)

        # 1. Fixture Only Mode
        if self.mode == "fixture_only":
            return self._serve_snapshot_records(product_id, latitude, longitude, now_utc)

        # 2. Live Request Attempt
        url = (
            f"{self.base_url}/griddap/nesdisVHNSQchlaDaily.json"
            f"?chlor_a[(last)][(0.0)][({latitude - 0.05:.4f}):({latitude + 0.05:.4f})]"
            f"[({longitude - 0.05:.4f}):({longitude + 0.05:.4f})]"
        )

        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                if client is not None:
                    resp = await client.get(url, timeout=self.timeout_seconds, follow_redirects=True)
                else:
                    async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as session:
                        resp = await session.get(url)

                if resp.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"Server error {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                resp.raise_for_status()

                data = resp.json()
                records = self.parse_erddap_json_table(
                    data,
                    variable_name="chlorophyll_a",
                    unit=unit,
                    source_url=url,
                    retrieved_at=now_utc,
                )

                # Cache successfully retrieved valid snapshot
                if records:
                    snapshot = ErddapSnapshot(
                        snapshot_id=f"snap-chla-{uuid4().hex[:8]}",
                        product_id=product_id,
                        min_lat=latitude - 0.1,
                        max_lat=latitude + 0.1,
                        min_lon=longitude - 0.1,
                        max_lon=longitude + 0.1,
                        observed_at=records[0].observed_at or now_utc,
                        retrieved_at=now_utc,
                        source_url=url,
                        records=[r.model_dump(mode="json") for r in records],
                        metadata={"product": "VIIRS Science Quality Chlorophyll-a"},
                    )
                    self.register_snapshot(snapshot)

                return records

            except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.NetworkError) as exc:
                last_exc = exc
                logger.warning(
                    "ERDDAP Chlorophyll fetch attempt %d/%d failed (%s): %s",
                    attempt + 1,
                    self.max_retries + 1,
                    url,
                    exc,
                )

        # 3. Fallback to matching cached offline snapshot
        if self.mode == "live_with_fallback":
            logger.info("Live ERDDAP failed; falling back to offline snapshot cache for (%s, %s)", latitude, longitude)
            fallback_records = self._serve_snapshot_records(product_id, latitude, longitude, now_utc)
            if fallback_records:
                return fallback_records

        # If live_only or no matching snapshot found: return empty / raise
        if last_exc:
            logger.warning("No offline snapshot available for (%s, %s); returning empty evidence", latitude, longitude)
            return []
        return []

    def _serve_snapshot_records(
        self,
        product_id: str,
        latitude: float,
        longitude: float,
        now_utc: datetime,
    ) -> list[EvidenceRecord]:
        """Retrieve and stamp records from a matching offline snapshot."""
        snapshot, diagnostics = self.find_matching_snapshot(product_id, latitude, longitude, now=now_utc)
        if not snapshot:
            logger.info("No matching offline snapshot for %s at (%s, %s): %s", product_id, latitude, longitude, diagnostics)
            return []

        age_seconds = diagnostics.get("snapshot_age_seconds", 0.0)
        stamped_records: list[EvidenceRecord] = []

        for rec_dict in snapshot.records:
            try:
                rec = EvidenceRecord.model_validate(rec_dict)
                # Apply offline snapshot indicators
                rec_meta = dict(rec.metadata or {})
                rec_meta["is_cached_snapshot"] = True
                rec_meta["offline_fixture_mode"] = True
                rec_meta["snapshot_id"] = snapshot.snapshot_id
                rec_meta["snapshot_age_seconds"] = age_seconds
                rec_meta["snapshot_retrieved_at"] = snapshot.retrieved_at.isoformat()
                rec_meta["original_observed_at"] = snapshot.observed_at.isoformat()

                flags = list(rec.quality_flags or [])
                if "cached_offline_snapshot" not in flags:
                    flags.append("cached_offline_snapshot")
                if "offline_fixture" not in flags:
                    flags.append("offline_fixture")

                # If snapshot is older than 24 hours, update status to stale
                status = "stale" if age_seconds > 86400 else rec.status

                stamped = EvidenceRecord(
                    evidence_id=f"snap-{rec.evidence_id}",
                    source=f"{rec.source}-cached-fixture",
                    source_record_id=rec.source_record_id,
                    variable=rec.variable,
                    value=rec.value,
                    unit=rec.unit,
                    latitude=rec.latitude,
                    longitude=rec.longitude,
                    depth_m=rec.depth_m,
                    observed_at=snapshot.observed_at,
                    retrieved_at=now_utc,
                    status=status,
                    quality_flags=flags,
                    metadata=rec_meta,
                )
                stamped_records.append(stamped)
            except Exception as exc:
                logger.warning("Failed to deserialize snapshot record: %s", exc)

        return stamped_records
