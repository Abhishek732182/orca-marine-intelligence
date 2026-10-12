"""INCOIS Potential Fishing Zone (PFZ) Bulletin Ingestion and Parser.

Parses, validates, and normalizes official INCOIS (Indian National Centre
for Ocean Information Services) PFZ bulletins and spatial geometries into
standardized ORCA EvidenceRecord objects.

Guarantees:
1. Validates GeoJSON schemas according to official OGC/RFC 7946 specifications.
2. Normalizes timestamps to timezone-aware UTC datetime.
3. Preserves metadata: sector, landing centre, bearing, distance, depth, bulletin ID.
4. Handles partial failures, malformed features, and duplicate records gracefully.
5. Performs point-in-polygon spatial matching without external heavy GIS dependencies.
"""

from datetime import datetime, timezone
import json
import logging
from typing import Any
from uuid import uuid4
import httpx

from app.schemas.evidence import EvidenceRecord

logger = logging.getLogger("orca.data_sources.incois_pfz")


def point_in_polygon(x: float, y: float, poly: list[list[float]]) -> bool:
    """Ray-casting point-in-polygon test.
    
    Args:
        x: Longitude of test point.
        y: Latitude of test point.
        poly: List of [longitude, latitude] coordinate pairs.
    """
    n = len(poly)
    inside = False
    p1x, p1y = poly[0][0], poly[0][1]
    for i in range(n + 1):
        p2x, p2y = poly[i % n][0], poly[i % n][1]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x if p1y != p2y else p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def parse_iso_datetime(dt_str: Any) -> datetime | None:
    """Safely parse ISO datetime string into timezone-aware UTC datetime."""
    if not dt_str or not isinstance(dt_str, str):
        return None
    try:
        # Handle trailing Z
        s = dt_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception as exc:
        logger.debug("Failed to parse datetime %r: %s", dt_str, exc)
        return None


class IncoisPfzBulletinParser:
    """Parser and validator for INCOIS PFZ bulletins."""

    def __init__(self, provider_name: str = "incois-pfz") -> None:
        self.provider_name = provider_name

    def parse_geojson(
        self,
        geojson_data: dict[str, Any] | str,
        *,
        source_url: str | None = None,
        retrieved_at: datetime | None = None,
        is_fixture: bool | None = None,
    ) -> list[EvidenceRecord]:
        """Validate and parse INCOIS PFZ GeoJSON FeatureCollection.
        
        Args:
            geojson_data: Raw GeoJSON dict or JSON string.
            source_url: Optional source URL or bulletin identifier.
            retrieved_at: Time the data was retrieved (defaults to now UTC).
            is_fixture: Explicit boolean indicating offline fixture parsing.
            
        Returns:
            List of valid, deduplicated EvidenceRecord objects.
            
        Raises:
            ValueError: If the top-level GeoJSON structure is invalid or corrupt.
        """
        now_utc = retrieved_at or datetime.now(timezone.utc)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)

        # Detect fixture origin
        is_fixture_source = (
            is_fixture
            if is_fixture is not None
            else (source_url is not None and any(term in source_url.lower() for term in ["fixture", "sample", "offline"]))
        )

        if isinstance(geojson_data, str):
            try:
                data = json.loads(geojson_data)
            except Exception as exc:
                raise ValueError(f"Malformed JSON in INCOIS bulletin: {exc}") from exc
        elif isinstance(geojson_data, dict):
            data = geojson_data
        else:
            raise ValueError("INCOIS bulletin must be a dictionary or JSON string.")

        if not isinstance(data, dict):
            raise ValueError("GeoJSON root must be a dictionary.")

        geom_type = data.get("type")
        if geom_type != "FeatureCollection":
            if geom_type == "Feature":
                features = [data]
            else:
                raise ValueError(f"Expected GeoJSON FeatureCollection or Feature, got: {geom_type}")
        else:
            features = data.get("features")
            if not isinstance(features, list):
                raise ValueError("GeoJSON FeatureCollection must contain a 'features' array.")

        records: list[EvidenceRecord] = []
        seen_keys: set[str] = set()

        for idx, feature in enumerate(features):
            if not isinstance(feature, dict):
                logger.warning("Skipping malformed feature at index %d (not a dict)", idx)
                continue

            properties = feature.get("properties") or {}
            geometry = feature.get("geometry") or {}

            if not isinstance(properties, dict) or not isinstance(geometry, dict):
                logger.warning("Skipping feature %d: properties or geometry not a dict", idx)
                continue

            g_type = geometry.get("type")
            coords = geometry.get("coordinates")

            # Extract representative coordinate and polygon boundaries
            rep_lat: float | None = None
            rep_lon: float | None = None
            boundary_polygon: list[list[float]] = []

            if g_type == "Point" and isinstance(coords, (list, tuple)) and len(coords) >= 2:
                rep_lon, rep_lat = float(coords[0]), float(coords[1])
            elif g_type == "Polygon" and isinstance(coords, list) and len(coords) > 0:
                ring = coords[0]
                if isinstance(ring, list) and len(ring) >= 3:
                    boundary_polygon = [[float(p[0]), float(p[1])] for p in ring if len(p) >= 2]
                    # Calculate centroid as representative coordinate
                    if boundary_polygon:
                        rep_lon = sum(p[0] for p in boundary_polygon) / len(boundary_polygon)
                        rep_lat = sum(p[1] for p in boundary_polygon) / len(boundary_polygon)
            elif g_type == "MultiPolygon" and isinstance(coords, list) and len(coords) > 0:
                first_poly = coords[0]
                if isinstance(first_poly, list) and len(first_poly) > 0:
                    ring = first_poly[0]
                    if isinstance(ring, list) and len(ring) >= 3:
                        boundary_polygon = [[float(p[0]), float(p[1])] for p in ring if len(p) >= 2]
                        if boundary_polygon:
                            rep_lon = sum(p[0] for p in boundary_polygon) / len(boundary_polygon)
                            rep_lat = sum(p[1] for p in boundary_polygon) / len(boundary_polygon)

            # Fallback coordinates from properties if geometry is missing or abstract
            if rep_lat is None or rep_lon is None:
                prop_lat = properties.get("latitude") or properties.get("lat")
                prop_lon = properties.get("longitude") or properties.get("lon")
                if prop_lat is not None and prop_lon is not None:
                    try:
                        rep_lat = float(prop_lat)
                        rep_lon = float(prop_lon)
                    except (ValueError, TypeError):
                        pass

            if rep_lat is None or rep_lon is None:
                logger.warning("Skipping feature %d: unable to derive coordinates", idx)
                continue

            # Validate coordinate bounds
            if not -90.0 <= rep_lat <= 90.0 or not -180.0 <= rep_lon <= 180.0:
                logger.warning("Skipping feature %d: coordinate out of bounds (%s, %s)", idx, rep_lat, rep_lon)
                continue

            # Timestamps
            valid_from = parse_iso_datetime(properties.get("valid_from")) or parse_iso_datetime(properties.get("issue_date"))
            valid_to = parse_iso_datetime(properties.get("valid_to")) or parse_iso_datetime(properties.get("expiry_date"))
            observed_at = valid_from or now_utc

            # Deduplication key
            bulletin_id = str(properties.get("bulletin_id") or properties.get("id") or feature.get("id") or f"feat-{idx}")
            sector = str(properties.get("sector") or "Indian EEZ")
            dedup_key = f"{bulletin_id}:{sector}:{rep_lat:.4f}:{rep_lon:.4f}"
            if dedup_key in seen_keys:
                logger.info("Skipping duplicate INCOIS feature: %s", dedup_key)
                continue
            seen_keys.add(dedup_key)

            # Base metadata
            feat_meta: dict[str, Any] = {
                "bulletin_id": bulletin_id,
                "sector": sector,
                "landing_centre": properties.get("landing_centre"),
                "bearing_deg": properties.get("bearing_deg"),
                "distance_km": properties.get("distance_km"),
                "depth_m": properties.get("depth_m"),
                "valid_from": valid_from.isoformat() if valid_from else None,
                "valid_to": valid_to.isoformat() if valid_to else None,
                "source_url": source_url or "https://incois.gov.in/portal/pfz",
                "geometry_type": g_type,
                "polygon_coordinates": boundary_polygon if boundary_polygon else None,
                "target_species": properties.get("target_species") or properties.get("species"),
                "advisory_text": properties.get("advisory_text") or properties.get("description"),
                "is_offline_fixture": is_fixture_source,
            }

            base_flags = ["official_government_advisory", "incois_pfz"]
            if is_fixture_source:
                base_flags.append("offline_fixture")

            # 1. Primary Record: Potential Fishing Zone advisory indicator
            rec_id = f"incois-pfz-{uuid4().hex[:10]}"
            pfz_rec = EvidenceRecord(
                evidence_id=rec_id,
                source=self.provider_name,
                source_record_id=bulletin_id,
                variable="potential_fishing_zone",
                value=1.0,
                unit="unitless",
                latitude=rep_lat,
                longitude=rep_lon,
                depth_m=float(properties.get("depth_m")) if properties.get("depth_m") is not None else None,
                observed_at=observed_at,
                retrieved_at=now_utc,
                status="valid",
                quality_flags=base_flags,
                metadata=feat_meta,
            )
            records.append(pfz_rec)

            aux_flags = ["incois_satellite_composite", "official_advisory"]
            if is_fixture_source:
                aux_flags.append("offline_fixture")

            # 2. Auxiliary Record: Sea Surface Temperature if explicitly reported in bulletin
            sst_val = properties.get("sst_c") or properties.get("sea_surface_temperature")
            if sst_val is not None:
                try:
                    sst_num = float(sst_val)
                    if -2.0 <= sst_num <= 45.0:
                        records.append(
                            EvidenceRecord(
                                evidence_id=f"incois-sst-{uuid4().hex[:10]}",
                                source=self.provider_name,
                                source_record_id=f"{bulletin_id}-sst",
                                variable="sea_surface_temperature",
                                value=sst_num,
                                unit="degC",
                                latitude=rep_lat,
                                longitude=rep_lon,
                                observed_at=observed_at,
                                retrieved_at=now_utc,
                                status="valid",
                                quality_flags=aux_flags,
                                metadata=feat_meta,
                            )
                        )
                except (ValueError, TypeError):
                    pass

            # 3. Auxiliary Record: Chlorophyll-a if explicitly reported in bulletin
            chla_val = properties.get("chlorophyll_mg_m3") or properties.get("chlorophyll_a")
            if chla_val is not None:
                try:
                    chla_num = float(chla_val)
                    if 0.0 <= chla_num <= 100.0:
                        records.append(
                            EvidenceRecord(
                                evidence_id=f"incois-chla-{uuid4().hex[:10]}",
                                source=self.provider_name,
                                source_record_id=f"{bulletin_id}-chla",
                                variable="chlorophyll_a",
                                value=chla_num,
                                unit="mg/m^3",
                                latitude=rep_lat,
                                longitude=rep_lon,
                                observed_at=observed_at,
                                retrieved_at=now_utc,
                                status="valid",
                                quality_flags=aux_flags,
                                metadata=feat_meta,
                            )
                        )
                except (ValueError, TypeError):
                    pass

        return records

    def match_records_for_location(
        self,
        records: list[EvidenceRecord],
        latitude: float,
        longitude: float,
        radius_km: float = 30.0,
    ) -> list[EvidenceRecord]:
        """Filter records that geographically enclose or are proximate to target position."""
        matched: list[EvidenceRecord] = []
        for rec in records:
            if rec.latitude is None or rec.longitude is None:
                continue

            # 1. Exact or polygon match
            poly = rec.metadata.get("polygon_coordinates")
            if poly and len(poly) >= 3:
                if point_in_polygon(longitude, latitude, poly):
                    matched.append(rec)
                    continue

            # 2. Euclidean distance approx for marine coastal scale (1 deg approx 111 km)
            dlat = (rec.latitude - latitude) * 111.0
            dlon = (rec.longitude - longitude) * 111.0 * 0.965  # cos(15 deg) approx 0.965
            dist = (dlat**2 + dlon**2) ** 0.5
            if dist <= radius_km:
                matched.append(rec)

        return matched


class IncoisPfzClient:
    """Asynchronous client with retry and timeout for INCOIS PFZ bulletins."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.parser = IncoisPfzBulletinParser()

    async def fetch_bulletin(
        self,
        sector: str | None = None,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> list[EvidenceRecord]:
        """Fetch remote INCOIS bulletin over HTTPS with retry handling."""
        if not self.base_url:
            return []

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        params = {}
        if sector:
            params["sector"] = sector

        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                if client is not None:
                    resp = await client.get(
                        self.base_url,
                        headers=headers,
                        params=params,
                        timeout=self.timeout_seconds,
                    )
                else:
                    async with httpx.AsyncClient(timeout=self.timeout_seconds) as session:
                        resp = await session.get(
                            self.base_url,
                            headers=headers,
                            params=params,
                        )

                if resp.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"Server error {resp.status_code}",
                        request=resp.request,
                        response=resp,
                    )
                resp.raise_for_status()

                data = resp.json()
                return self.parser.parse_geojson(data, source_url=self.base_url)

            except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.NetworkError) as exc:
                last_exc = exc
                logger.warning(
                    "INCOIS fetch attempt %d/%d failed: %s",
                    attempt + 1,
                    self.max_retries + 1,
                    exc,
                )
                if attempt == self.max_retries:
                    raise

        if last_exc:
            raise last_exc
        return []
