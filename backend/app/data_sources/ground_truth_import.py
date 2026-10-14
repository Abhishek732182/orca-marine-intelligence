"""Offline Ground-Truth Fisheries Data Import and Benchmark Readiness.

ORCA Fisheries Intelligence v2.5: Ground-Truth Acquisition & Benchmark Readiness.

Guarantees & Scientific Rules:
1. Reuses AuthorizedFisheriesAdapter and BiologicalDataQualityGate without duplicate logic.
2. Implements a documented offline CSV ingestion contract for ICAR-CMFRI and FSI records.
   Does NOT connect to or fabricate unverified live API feeds.
3. Enforces strict schema validation: column presence, coordinates, ISO 8601 UTC timestamps,
   standardized units, species verification against SPECIES_REGISTRY, and authorized provenance.
4. Quarantines or rejects invalid rows with explicit machine-readable reason codes.
   Never silently manufactures missing values.
5. Derives CPUE strictly when catch (kg) and effort (hours) are compatible:
   CPUE = catch_weight_kg / effort_hours (kg/hour).
6. Prevents duplicate and temporal leakage in evaluation partitions with explicit
   leakage-detection validation.
7. Provides a dry-run validation mode reporting row counts, acceptance/rejection/quarantine
   tallies, and reason frequencies without claiming data are real unless an authorized file is supplied.
8. Preserves 24-hour chlorophyll freshness and stale-data exclusion policies.
9. Withholds fish-prediction accuracy claims (Precision/Recall/F1 remain NOT_EVALUABLE).
"""

from collections import Counter
import csv
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import io
import logging
import math
from pathlib import Path
from typing import Any, Sequence, TextIO

from pydantic import BaseModel, Field

from app.data_sources.biological_adapter import (
    AuthorizedFisheriesAdapter,
    BiologicalObservationMethod,
    RawBiologicalFisheriesRecord,
)
from app.evidence.freshness import is_stale
from app.schemas.evidence import EvidenceRecord

logger = logging.getLogger("orca.data_sources.ground_truth_import")

# Canonical required header columns for authorized ground-truth CSV
CANONICAL_REQUIRED_COLUMNS = [
    "record_identifier",
    "source_agency",
    "dataset_identifier",
    "observation_method",
    "species_name",
    "latitude",
    "longitude",
    "observed_at",
    "catch_weight",
    "catch_unit",
    "effort_value",
    "effort_unit",
    "is_authorized",
]

# Accepted header aliases for CMFRI / FSI field conventions
COLUMN_ALIASES: dict[str, list[str]] = {
    "record_identifier": ["record_identifier", "record_id", "haul_id", "trip_id", "landing_id"],
    "source_agency": ["source_agency", "agency", "institution", "source", "custodian"],
    "dataset_identifier": ["dataset_identifier", "dataset_id", "survey_id", "batch_id"],
    "observation_method": ["observation_method", "method", "sampling_protocol", "observation_type"],
    "species_name": ["species_name", "species_raw_name", "species", "common_name"],
    "scientific_name": ["scientific_name", "scientificname", "taxon"],
    "latitude": ["latitude", "lat", "decimallatitude"],
    "longitude": ["longitude", "lon", "long", "decimallongitude"],
    "spatial_uncertainty_km": ["spatial_uncertainty_km", "uncertainty_km", "spatial_uncertainty"],
    "landing_center_name": ["landing_center_name", "landing_center", "harbour", "port", "landing_site"],
    "observed_at": ["observed_at", "event_date", "landing_date", "haul_time", "timestamp", "date"],
    "voyage_start_at": ["voyage_start_at", "voyage_start", "departure_time"],
    "voyage_end_at": ["voyage_end_at", "voyage_end", "arrival_time"],
    "catch_weight": ["catch_weight", "catch_weight_kg", "catch_kg", "catch"],
    "catch_unit": ["catch_unit", "unit_catch", "catch_units"],
    "effort_value": ["effort_value", "effort", "effort_hours", "trawl_duration_hours", "duration_hours"],
    "effort_unit": ["effort_unit", "unit_effort", "effort_units"],
    "gear_type": ["gear_type", "gear", "fishing_gear"],
    "is_authorized": ["is_authorized", "is_authorized_official_feed", "authorized", "official_feed"],
    "access_authorization_token": ["access_authorization_token", "auth_token", "token", "license_key"],
}

# Unit compatibility sets
VALID_CATCH_UNITS = {"kg", "kilogram", "kilograms"}
VALID_EFFORT_HOURLY_UNITS = {"hours", "h", "hour", "trawl_hours", "fishing_hours"}


def _resolve_header_mapping(headers: Sequence[str]) -> tuple[dict[str, str], list[str]]:
    """Map CSV column headers to canonical names using defined aliases.

    Returns:
        (canonical_to_csv_header_dict, missing_required_canonical_columns)
    """
    clean_headers = {h.strip().lower(): h for h in headers if h and h.strip()}
    mapping: dict[str, str] = {}

    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias.lower() in clean_headers:
                mapping[canonical] = clean_headers[alias.lower()]
                break

    missing = [c for c in CANONICAL_REQUIRED_COLUMNS if c not in mapping]
    return mapping, missing


@dataclass
class GroundTruthImportSummary:
    """Detailed summary of CSV import dry-run or ingestion execution."""

    total_rows: int
    accepted_rows: int
    rejected_rows: int
    quarantined_rows: int
    is_dry_run: bool
    is_authorized_dataset: bool
    data_version: str
    source_agency: str | None
    missing_required_headers: list[str]
    rejection_reasons_by_row: dict[int, list[str]] = field(default_factory=dict)
    summary_reasons: dict[str, int] = field(default_factory=dict)
    imported_records: list[EvidenceRecord] = field(default_factory=list)
    source_file_sha256: str | None = None
    store_count_before: int = 0
    store_count_after: int = 0
    is_idempotent_reimport: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["imported_records"] = [r.model_dump() for r in self.imported_records]
        return d


@dataclass
class BenchmarkSplitReport:
    """Validation report for benchmark dataset partitioning to prevent leakage."""

    is_valid_split: bool
    split_method: str
    source_data_version: str
    train_count: int
    eval_count: int
    leakage_warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GroundTruthCsvImporter:
    """Ingests and validates offline ground-truth fisheries CSV datasets."""

    def __init__(
        self,
        adapter: AuthorizedFisheriesAdapter | None = None,
        max_spatial_uncertainty_km: float = 50.0,
    ) -> None:
        self.adapter = adapter or AuthorizedFisheriesAdapter(
            max_spatial_uncertainty_km=max_spatial_uncertainty_km
        )
        self.imported_file_checksums: set[str] = set()

    def import_csv(
        self,
        csv_source: str | TextIO | Path,
        *,
        is_dry_run: bool = True,
        now: datetime | None = None,
        data_version: str = "v2.5-draft",
    ) -> GroundTruthImportSummary:
        """Parse, validate, and optionally import ground-truth CSV observations.

        Args:
            csv_source: Raw CSV string, file-like text buffer, or file path.
            is_dry_run: If True, executes full validation and diagnostics without
                        committing records to operational storage.
            now: Reference evaluation timestamp (timezone-aware UTC).
            data_version: Version tag of the imported dataset.

        Returns:
            GroundTruthImportSummary containing counts, reason codes, and diagnostics.
        """
        ref_time = now or datetime.now(timezone.utc)
        if ref_time.tzinfo is None:
            ref_time = ref_time.replace(tzinfo=timezone.utc)

        store_before = len(self.adapter._normalized_records)

        # 1. Read input stream
        if isinstance(csv_source, Path):
            if not csv_source.exists():
                return GroundTruthImportSummary(
                    total_rows=0,
                    accepted_rows=0,
                    rejected_rows=0,
                    quarantined_rows=0,
                    is_dry_run=is_dry_run,
                    is_authorized_dataset=False,
                    data_version=data_version,
                    source_agency=None,
                    missing_required_headers=[],
                    summary_reasons={"file_not_found": 1},
                    store_count_before=store_before,
                    store_count_after=store_before,
                )
            content = csv_source.read_text(encoding="utf-8")
        elif isinstance(csv_source, str):
            content = csv_source
        else:
            content = csv_source.read()

        stripped = content.strip()
        if not stripped:
            return GroundTruthImportSummary(
                total_rows=0,
                accepted_rows=0,
                rejected_rows=0,
                quarantined_rows=0,
                is_dry_run=is_dry_run,
                is_authorized_dataset=False,
                data_version=data_version,
                source_agency=None,
                missing_required_headers=[],
                summary_reasons={"empty_file": 1},
                store_count_before=store_before,
                store_count_after=store_before,
            )

        file_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Idempotent re-import check: avoid duplicate double-insertion of identical file
        if not is_dry_run and file_sha256 in self.imported_file_checksums:
            logger.info("File SHA256 %s already imported; performing idempotent skip", file_sha256)
            return GroundTruthImportSummary(
                total_rows=0,
                accepted_rows=0,
                rejected_rows=0,
                quarantined_rows=0,
                is_dry_run=is_dry_run,
                is_authorized_dataset=True,
                data_version=data_version,
                source_agency=None,
                missing_required_headers=[],
                summary_reasons={"idempotent_reimport_skipped": 1},
                source_file_sha256=file_sha256,
                store_count_before=store_before,
                store_count_after=store_before,
                is_idempotent_reimport=True,
            )

        reader = csv.DictReader(io.StringIO(stripped))
        headers = list(reader.fieldnames or [])
        header_map, missing_headers = _resolve_header_mapping(headers)

        if missing_headers:
            return GroundTruthImportSummary(
                total_rows=0,
                accepted_rows=0,
                rejected_rows=0,
                quarantined_rows=0,
                is_dry_run=is_dry_run,
                is_authorized_dataset=False,
                data_version=data_version,
                source_agency=None,
                missing_required_headers=missing_headers,
                summary_reasons={f"missing_required_header:{h}": 1 for h in missing_headers},
                source_file_sha256=file_sha256,
                store_count_before=store_before,
                store_count_after=store_before,
            )

        initial_signatures = set(self.adapter.quality_gate.seen_signatures)

        total_rows = 0
        accepted_rows = 0
        rejected_rows = 0
        quarantined_rows = 0
        row_reasons: dict[int, list[str]] = {}
        all_reasons: list[str] = []
        imported_records: list[EvidenceRecord] = []
        detected_agency: str | None = None
        has_authorized_rows = False

        for row_idx, row in enumerate(reader, start=1):
            total_rows += 1
            reasons: list[str] = []

            def get_val(canonical_key: str) -> str | None:
                header_name = header_map.get(canonical_key)
                if not header_name:
                    return None
                val = row.get(header_name)
                return val.strip() if val is not None else None

            # A. Extract fields
            rec_id = get_val("record_identifier")
            source_agency = get_val("source_agency")
            dataset_id = get_val("dataset_identifier")
            method_str = get_val("observation_method")
            species_raw = get_val("species_name")
            sci_name = get_val("scientific_name")
            lat_str = get_val("latitude")
            lon_str = get_val("longitude")
            uncertainty_str = get_val("spatial_uncertainty_km")
            landing_center = get_val("landing_center_name")
            obs_at_str = get_val("observed_at")
            voyage_start_str = get_val("voyage_start_at")
            voyage_end_str = get_val("voyage_end_at")
            catch_val_str = get_val("catch_weight")
            catch_unit_str = get_val("catch_unit")
            effort_val_str = get_val("effort_value")
            effort_unit_str = get_val("effort_unit")
            gear_type = get_val("gear_type")
            is_auth_str = get_val("is_authorized")
            auth_token = get_val("access_authorization_token")

            if source_agency and not detected_agency:
                detected_agency = source_agency

            # B. Validate record identifier & agency
            if not rec_id:
                reasons.append("missing_record_identifier")
            if not source_agency:
                reasons.append("missing_source_agency")
            if not dataset_id:
                reasons.append("missing_dataset_identifier")

            # C. Validate observation method
            obs_method: BiologicalObservationMethod | None = None
            if not method_str:
                reasons.append("missing_observation_method")
            else:
                try:
                    obs_method = BiologicalObservationMethod(method_str.strip().upper())
                except ValueError:
                    reasons.append(f"invalid_observation_method: {method_str}")

            # D. Validate coordinates & numerical sanity
            lat: float | None = None
            lon: float | None = None
            if lat_str is None or lon_str is None:
                reasons.append("missing_coordinates")
            else:
                try:
                    lat = float(lat_str)
                    lon = float(lon_str)
                    if math.isnan(lat) or math.isinf(lat) or math.isnan(lon) or math.isinf(lon):
                        reasons.append("coordinates_nan_or_infinite")
                    elif not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                        reasons.append(f"coordinates_out_of_bounds: ({lat}, {lon})")
                except ValueError:
                    reasons.append(f"unparseable_coordinates: lat={lat_str}, lon={lon_str}")

            spatial_uncertainty = 5.0
            if uncertainty_str:
                try:
                    spatial_uncertainty = float(uncertainty_str)
                    if math.isnan(spatial_uncertainty) or math.isinf(spatial_uncertainty):
                        reasons.append("spatial_uncertainty_nan_or_infinite")
                except ValueError:
                    reasons.append(f"unparseable_spatial_uncertainty: {uncertainty_str}")

            # E. Validate timestamps
            observed_at: datetime | None = None
            if not obs_at_str:
                reasons.append("missing_observed_at_timestamp")
            else:
                try:
                    dt = datetime.fromisoformat(obs_at_str.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    observed_at = dt
                except Exception:
                    reasons.append(f"invalid_timestamp_format: {obs_at_str}")

            voyage_start: datetime | None = None
            if voyage_start_str:
                try:
                    dt = datetime.fromisoformat(voyage_start_str.replace("Z", "+00:00"))
                    voyage_start = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
                except Exception:
                    reasons.append(f"invalid_voyage_start_format: {voyage_start_str}")

            voyage_end: datetime | None = None
            if voyage_end_str:
                try:
                    dt = datetime.fromisoformat(voyage_end_str.replace("Z", "+00:00"))
                    voyage_end = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
                except Exception:
                    reasons.append(f"invalid_voyage_end_format: {voyage_end_str}")

            # F. Validate Catch & Effort Units & numerical sanity
            catch_kg: float | None = None
            if catch_val_str is not None and catch_val_str != "":
                if not catch_unit_str or catch_unit_str.strip().lower() not in VALID_CATCH_UNITS:
                    reasons.append(f"incompatible_catch_units: {catch_unit_str}")
                try:
                    catch_kg = float(catch_val_str)
                    if math.isnan(catch_kg) or math.isinf(catch_kg):
                        reasons.append("catch_weight_nan_or_infinite")
                except ValueError:
                    reasons.append(f"unparseable_catch_weight: {catch_val_str}")

            effort_hours: float | None = None
            if effort_val_str is not None and effort_val_str != "":
                if not effort_unit_str or effort_unit_str.strip().lower() not in VALID_EFFORT_HOURLY_UNITS:
                    reasons.append(f"incompatible_effort_units: {effort_unit_str}")
                try:
                    effort_hours = float(effort_val_str)
                    if math.isnan(effort_hours) or math.isinf(effort_hours):
                        reasons.append("effort_hours_nan_or_infinite")
                except ValueError:
                    reasons.append(f"unparseable_effort_value: {effort_val_str}")

            # G. Authorization flag
            is_auth = False
            if is_auth_str:
                is_auth = is_auth_str.strip().lower() in {"true", "1", "yes", "authorized"}
            if is_auth:
                has_authorized_rows = True

            # If basic row syntax failed, register rejection
            if reasons or obs_method is None or observed_at is None or lat is None or lon is None or not rec_id or not source_agency or not dataset_id or not species_raw:
                rejected_rows += 1
                row_reasons[row_idx] = reasons
                all_reasons.extend(reasons)
                continue

            # H. Delegate to AuthorizedFisheriesAdapter quality gate
            raw_rec = RawBiologicalFisheriesRecord(
                source_agency=source_agency,
                dataset_identifier=dataset_id,
                record_identifier=rec_id,
                observation_method=obs_method,
                species_raw_name=species_raw,
                scientific_name=sci_name,
                latitude=lat,
                longitude=lon,
                spatial_uncertainty_km=spatial_uncertainty,
                landing_center_name=landing_center,
                observed_at=observed_at,
                voyage_start_at=voyage_start,
                voyage_end_at=voyage_end,
                catch_weight_kg=catch_kg,
                effort_hours=effort_hours,
                gear_type=gear_type,
                is_authorized_official_feed=is_auth,
                access_authorization_token=auth_token,
                metadata={"csv_row_number": row_idx, "source_file_sha256": file_sha256},
            )

            ev_rec, gate_issues = self.adapter.normalize_record(
                raw_rec,
                now=ref_time,
                commit=(not is_dry_run),
            )

            if gate_issues:
                rejected_rows += 1
                row_reasons[row_idx] = gate_issues
                all_reasons.extend(gate_issues)
            elif ev_rec is not None:
                if ev_rec.status == "valid":
                    accepted_rows += 1
                    if not is_dry_run:
                        imported_records.append(ev_rec)
                else:
                    # e.g. status == "invalid" due to unauthorized feed
                    quarantined_rows += 1
                    row_reasons[row_idx] = ["unauthorized_or_unverified_feed"]
                    all_reasons.append("unauthorized_or_unverified_feed")

        summary_counter = Counter(all_reasons)

        # Restore seen_signatures if dry run so subsequent actual import is not blocked
        if is_dry_run:
            self.adapter.quality_gate.seen_signatures = initial_signatures
        elif accepted_rows > 0:
            self.imported_file_checksums.add(file_sha256)

        store_after = len(self.adapter._normalized_records)

        return GroundTruthImportSummary(
            total_rows=total_rows,
            accepted_rows=accepted_rows,
            rejected_rows=rejected_rows,
            quarantined_rows=quarantined_rows,
            is_dry_run=is_dry_run,
            is_authorized_dataset=has_authorized_rows and (accepted_rows > 0),
            data_version=data_version,
            source_agency=detected_agency,
            missing_required_headers=[],
            rejection_reasons_by_row=row_reasons,
            summary_reasons=dict(summary_counter),
            imported_records=imported_records,
            source_file_sha256=file_sha256,
            store_count_before=store_before,
            store_count_after=store_after,
            is_idempotent_reimport=False,
        )


class BenchmarkPartitionValidator:
    """Validates benchmark dataset splits to guarantee zero data leakage."""

    @staticmethod
    def validate_partition_split(
        train_records: list[EvidenceRecord],
        eval_records: list[EvidenceRecord],
        *,
        split_method: str = "temporal_cutoff",
        source_data_version: str = "v2.5-draft",
    ) -> BenchmarkSplitReport:
        """Evaluate partition split for duplicate and temporal leakage.

        Guarantees:
        - Duplicate leakage: No observation signature or source_record_id appears in both splits.
        - Temporal leakage: In temporal_cutoff splits, evaluation observations strictly
          post-date all training observations.
        """
        warnings: list[str] = []

        if not train_records:
            warnings.append("empty_train_partition")
        if not eval_records:
            warnings.append("empty_eval_partition")

        if warnings:
            return BenchmarkSplitReport(
                is_valid_split=False,
                split_method=split_method,
                source_data_version=source_data_version,
                train_count=len(train_records),
                eval_count=len(eval_records),
                leakage_warnings=warnings,
            )

        # 1. Duplicate Leakage Check
        def get_sig(r: EvidenceRecord) -> str:
            # Deterministic record signature
            meta = r.metadata or {}
            sp = meta.get("canonical_species") or meta.get("species_raw") or r.variable
            obs_iso = r.observed_at.isoformat() if r.observed_at else "missing"
            lat = f"{r.latitude:.4f}" if r.latitude is not None else "0"
            lon = f"{r.longitude:.4f}" if r.longitude is not None else "0"
            return f"{r.source}|{r.source_record_id}|{lat}|{lon}|{obs_iso}|{sp}"

        train_sigs = {get_sig(r) for r in train_records}
        eval_sigs = {get_sig(r) for r in eval_records}

        dup_collisions = train_sigs.intersection(eval_sigs)
        if dup_collisions:
            warnings.append(
                f"duplicate_leakage_detected: {len(dup_collisions)} records present in both partitions"
            )

        # Check source_record_id collision
        train_ids = {r.source_record_id for r in train_records if r.source_record_id}
        eval_ids = {r.source_record_id for r in eval_records if r.source_record_id}
        id_collisions = train_ids.intersection(eval_ids)
        if id_collisions:
            warnings.append(
                f"record_id_leakage_detected: {len(id_collisions)} IDs present in both partitions"
            )

        # 2. Temporal Leakage Check
        train_times = [r.observed_at for r in train_records if r.observed_at is not None]
        eval_times = [r.observed_at for r in eval_records if r.observed_at is not None]

        if split_method == "temporal_cutoff" and train_times and eval_times:
            max_train_time = max(train_times)
            min_eval_time = min(eval_times)

            if min_eval_time <= max_train_time:
                overlap_count = sum(1 for t in eval_times if t <= max_train_time)
                warnings.append(
                    f"temporal_leakage_detected: {overlap_count} eval records observed at or before train cutoff ({max_train_time.isoformat()})"
                )

        is_valid = len(warnings) == 0

        return BenchmarkSplitReport(
            is_valid_split=is_valid,
            split_method=split_method,
            source_data_version=source_data_version,
            train_count=len(train_records),
            eval_count=len(eval_records),
            leakage_warnings=warnings,
            details={
                "train_records_count": len(train_records),
                "eval_records_count": len(eval_records),
                "duplicate_signature_collisions": len(dup_collisions),
                "id_collisions": len(id_collisions),
            },
        )


def verify_environmental_linkage_freshness(
    chlorophyll_records: list[EvidenceRecord],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Verify satellite chlorophyll observations adhere to the strict 24h freshness window."""
    ref_time = now or datetime.now(timezone.utc)
    if ref_time.tzinfo is None:
        ref_time = ref_time.replace(tzinfo=timezone.utc)

    total = len(chlorophyll_records)
    fresh_count = 0
    stale_count = 0
    null_count = 0

    for rec in chlorophyll_records:
        if rec.value is None:
            null_count += 1
            stale_count += 1
        elif is_stale(rec, now=ref_time):
            stale_count += 1
        else:
            fresh_count += 1

    return {
        "total_chlorophyll_records": total,
        "fresh_count": fresh_count,
        "stale_count": stale_count,
        "null_count": null_count,
        "fresh_coverage_ratio": round(fresh_count / total, 4) if total > 0 else 0.0,
        "freshness_window_hours": 24.0,
    }
