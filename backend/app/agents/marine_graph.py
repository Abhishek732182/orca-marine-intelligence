"""ORCA Marine Intelligence Agent.
A LangGraph-based workflow that fetches live marine forecast data, validates
and normalizes evidence, performs sea-state analysis using documented WMO
meteorological rules, and generates grounded advisories.
"""
from datetime import datetime, timezone
from typing import Any, cast
from typing_extensions import NotRequired, Required, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from app.agents.advisory_generator import generate_advisory
from app.agents.sea_state_rules import classify_sea_state
from app.data_sources.open_meteo_marine import OpenMeteoMarineProvider
from app.evidence.normalizer import normalize_evidence
from app.evidence.provenance import create_provenance
from app.evidence.validator import validate_evidence
from app.schemas.evidence import EvidenceRecord
class MarineState(TypedDict):
    """Shared state for the single ORCA Marine Intelligence Agent workflow."""
    # Input parameters
    location_name: NotRequired[str]
    latitude: Required[float]
    longitude: Required[float]
    forecast_time_window_hours: NotRequired[int]
    # Workflow execution tracking
    step_progress: NotRequired[list[str]]
    # Data collection & evidence
    evidence: NotRequired[list[EvidenceRecord]]
    provenance_records: NotRequired[list[dict[str, Any]]]
    issues: NotRequired[list[str]]
    result_status: NotRequired[str]
    summary: NotRequired[str]
    # Analysis & output
    measurements: NotRequired[dict[str, Any]]
    analysis: NotRequired[dict[str, Any]]
    limitations: NotRequired[list[str]]
    advisory: NotRequired[str]
    structured_output: NotRequired[dict[str, Any]]
# Preserved module-level provider instance for test compatibility
provider = OpenMeteoMarineProvider()
DISCLAIMERS_AND_LIMITATIONS = [
    "Wave height is a single sea-state parameter and does NOT determine overall fishing, maritime, or navigation safety.",
    "Small craft and fishing vessel safety requires evaluating wind velocity, wind gusts, wave steepness, swell direction, tidal streams, currents, and vessel tonnage.",
    "Values represent numerical weather prediction model output (Open-Meteo Marine / ECMWF / Meteo-France) and may differ from localized in-situ oceanographic buoy observations.",
    "ORCA does not issue official government meteorological warnings, cyclone alerts, or severe weather clearances. Mariners must consult the India Meteorological Department (IMD) / NOAA / Coast Guard before sailing.",
]
async def validate_input_node(state: MarineState) -> dict[str, Any]:
    """Step 1: Validate input coordinates and parameters."""
    lat = state["latitude"]
    lon = state["longitude"]
    loc_name = state.get("location_name", "Offshore Marine Location")
    window = state.get("forecast_time_window_hours", 24)
    progress = list(state.get("step_progress", []))
    issues = list(state.get("issues", []))
    if not -90 <= lat <= 90:
        issues.append(f"invalid_latitude: {lat}")
    if not -180 <= lon <= 180:
        issues.append(f"invalid_longitude: {lon}")
    if window < 1 or window > 168:
        issues.append(f"invalid_time_window_hours: {window}")
    progress.append(
        f"[STEP 1/5] Validated input: location='{loc_name}', "
        f"lat={lat:.4f}, lon={lon:.4f}, window={window}h"
    )
    return {
        "location_name": loc_name,
        "forecast_time_window_hours": window,
        "step_progress": progress,
        "issues": issues,
    }
async def collect_marine_data(state: MarineState) -> dict[str, Any]:
    """Step 2: Fetch wave-height forecast evidence from provider."""
    progress = list(state.get("step_progress", []))
    issues = list(state.get("issues", []))
    if issues:
        progress.append("[STEP 2/5] Skipped collection due to input validation issues.")
        return {
            "evidence": [],
            "issues": issues,
            "step_progress": progress,
            "result_status": "insufficient_evidence",
        }
    try:
        records = await provider.fetch(
            latitude=state["latitude"],
            longitude=state["longitude"],
        )
        window_hours = state.get("forecast_time_window_hours", 24)
        if records and len(records) > window_hours:
            records = records[:window_hours]
        if not records:
            issues.append("provider_returned_no_sea_records")
            progress.append(
                "[STEP 2/5] Live provider returned 0 records (coordinates may be on land or outside sea mask)."
            )
        else:
            progress.append(
                f"[STEP 2/5] Successfully retrieved {len(records)} wave-height records from {provider.provider_name}."
            )
        return {
            "evidence": records,
            "issues": issues,
            "step_progress": progress,
        }
    except Exception as exc:
        # Preserve provider failures; never turn them into safe weather results
        issues.append(f"data_provider_error: {type(exc).__name__}: {str(exc)}")
        progress.append(f"[STEP 2/5] Data provider error: {type(exc).__name__}")
        return {
            "evidence": [],
            "issues": issues,
            "step_progress": progress,
            "result_status": "insufficient_evidence",
        }
def normalize_and_validate_evidence(state: MarineState) -> dict[str, Any]:
    """Step 3: Normalize and validate returned evidence quality."""
    records = list(state.get("evidence", []))
    issues = list(state.get("issues", []))
    progress = list(state.get("step_progress", []))
    if not records:
        progress.append("[STEP 3/5] No records available to normalize; status marked insufficient_evidence.")
        return {
            "evidence": [],
            "provenance_records": [],
            "issues": issues,
            "result_status": "insufficient_evidence",
            "summary": (
                "No usable wave-height records were returned. "
                "Conditions cannot be assessed from this source."
            ),
            "step_progress": progress,
        }
    normalized_records: list[EvidenceRecord] = []
    provenance_records: list[dict[str, Any]] = []
    for record in records:
        # Step 3a: Canonical normalization
        try:
            record_dict = record.model_dump(mode="python")
            normalized = normalize_evidence(record_dict)
            normalized_records.append(normalized)
        except Exception as norm_err:
            issues.append(f"normalization_error: {str(norm_err)}")
            normalized = record
            normalized_records.append(normalized)
        # Step 3b: Provenance tracking
        prov = create_provenance(
            normalized,
            transformations=["canonical_normalized", "quality_checked"],
            metadata={"agent": "ORCA Marine Intelligence Agent"},
        )
        provenance_records.append(prov.model_dump(mode="python"))
        # Step 3c: Validation
        record_issues = validate_evidence(normalized)
        # For forecast records, observation time in future is expected
        if "forecast_data" in normalized.quality_flags:
            record_issues = [
                i for i in record_issues
                if i not in ("observation_time_in_future", "observation_after_retrieval")
            ]
        if normalized.status == "stale":
            record_issues.append("evidence_status_stale")
        if normalized.retrieved_at and (datetime.now(timezone.utc) - normalized.retrieved_at).total_seconds() > 86400:
            record_issues.append("evidence_retrieval_stale")
        if normalized.value is None or not isinstance(normalized.value, (int, float)):
            record_issues.append("missing_wave_height_value")
        issues.extend(record_issues)
    if issues:
        status = "evidence_requires_review"
        summary = (
            "Marine evidence was retrieved, but quality issues "
            "must be reviewed before it is used for an advisory."
        )
    else:
        status = "valid"
        summary = (
            f"Retrieved and verified {len(normalized_records)} wave-height forecast records. "
            "This is evidence retrieval, not a fishing or navigation safety clearance."
        )
    progress.append(f"[STEP 3/5] Normalized and validated {len(normalized_records)} records. Status: {status}")
    return {
        "evidence": normalized_records,
        "provenance_records": provenance_records,
        "issues": issues,
        "result_status": status,
        "summary": summary,
        "step_progress": progress,
    }
def analyze_wave_conditions(state: MarineState) -> dict[str, Any]:
    """Step 4: Analyze wave conditions using documented WMO Code Table 3700 rules."""
    records = state.get("evidence", [])
    result_status = state.get("result_status", "insufficient_evidence")
    progress = list(state.get("step_progress", []))
    if not records or result_status == "insufficient_evidence":
        progress.append("[STEP 4/5] Wave condition analysis: UNKNOWN (insufficient evidence).")
        measurements: dict[str, Any] = {
            "variable": "wave_height",
            "unit": "m",
            "sample_count": 0,
            "min_wave_height_m": None,
            "max_wave_height_m": None,
            "avg_wave_height_m": None,
            "latest_wave_height_m": None,
            "timeseries": [],
        }
        analysis: dict[str, Any] = {
            "sea_state_code": None,
            "sea_state_category": "UNKNOWN",
            "rule_standard": "WMO Code Table 3700 / Douglas Sea Scale",
            "description": "Classification unavailable due to absence of valid marine evidence.",
        }
        return {
            "measurements": measurements,
            "analysis": analysis,
            "step_progress": progress,
        }
    valid_values = [
        float(r.value)
        for r in records
        if r.value is not None and isinstance(r.value, (int, float))
    ]
    if not valid_values:
        progress.append("[STEP 4/5] Wave condition analysis: UNKNOWN (all values null).")
        timeseries = [
            {
                "timestamp": r.observed_at.isoformat() if r.observed_at else "unknown",
                "wave_height": None,
            }
            for r in records
        ]
        measurements = {
            "variable": "wave_height",
            "unit": "m",
            "sample_count": 0,
            "min_wave_height_m": None,
            "max_wave_height_m": None,
            "avg_wave_height_m": None,
            "latest_wave_height_m": None,
            "timeseries": timeseries,
        }
        analysis = {
            "sea_state_code": None,
            "sea_state_category": "UNKNOWN",
            "rule_standard": "WMO Code Table 3700 / Douglas Sea Scale",
            "description": "All wave height measurements were null.",
        }
        return {
            "measurements": measurements,
            "analysis": analysis,
            "result_status": "insufficient_evidence",
            "step_progress": progress,
        }
    min_h = round(min(valid_values), 2)
    max_h = round(max(valid_values), 2)
    avg_h = round(sum(valid_values) / len(valid_values), 2)
    latest_h = round(valid_values[-1], 2)
    timeseries = [
        {
            "timestamp": r.observed_at.isoformat() if r.observed_at else "unknown",
            "wave_height": float(r.value) if r.value is not None else None,
        }
        for r in records
    ]
    # Classify sea state based on peak/max forecast wave height
    sea_state = classify_sea_state(max_h)
    measurements = {
        "variable": "wave_height",
        "unit": "m",
        "sample_count": len(valid_values),
        "min_wave_height_m": min_h,
        "max_wave_height_m": max_h,
        "avg_wave_height_m": avg_h,
        "latest_wave_height_m": latest_h,
        "timeseries": timeseries,
    }
    analysis = {
        "sea_state_code": sea_state["wmo_code"],
        "sea_state_category": sea_state["category"],
        "rule_standard": sea_state["rule_standard"],
        "description": sea_state["description"],
    }
    progress.append(
        f"[STEP 4/5] Analyzed wave conditions: Range={min_h}m-{max_h}m, Avg={avg_h}m. "
        f"WMO Sea State: Code {sea_state['wmo_code']} ({sea_state['category']})"
    )
    return {
        "measurements": measurements,
        "analysis": analysis,
        "step_progress": progress,
    }
async def generate_advisory_report(state: MarineState) -> dict[str, Any]:
    """Step 5: Generate advisory report and compile final structured JSON."""
    progress = list(state.get("step_progress", []))
    location_name = state.get("location_name", "Offshore Marine Location")
    lat = state["latitude"]
    lon = state["longitude"]
    window = state.get("forecast_time_window_hours", 24)
    result_status = state.get("result_status", "insufficient_evidence")
    measurements = state.get("measurements", {})
    analysis = state.get("analysis", {})
    issues = state.get("issues", [])
    records = state.get("evidence", [])
    advisory_text, mode = await generate_advisory(
        location_name=location_name,
        latitude=lat,
        longitude=lon,
        forecast_time_window_hours=window,
        result_status=result_status,
        measurements=measurements,
        sea_state=analysis,
        issues=issues,
    )
    progress.append(f"[STEP 5/5] Advisory report synthesized (Generation mode: {mode}).")
    # Determine timestamps
    retrieved_at_iso = datetime.now(timezone.utc).isoformat()
    forecast_start = records[0].observed_at.isoformat() if records and records[0].observed_at else None
    forecast_end = records[-1].observed_at.isoformat() if records and records[-1].observed_at else None
    # Grid coordinates if available in metadata
    grid_lat = None
    grid_lon = None
    if records and records[0].metadata:
        grid_lat = records[0].metadata.get("model_grid_latitude")
        grid_lon = records[0].metadata.get("model_grid_longitude")
    quality_flags: list[str] = []
    if records:
        for r in records:
            quality_flags.extend(r.quality_flags)
    quality_flags = sorted(list(set(quality_flags)))
    analysis_payload = {
        "sea_state_code": analysis.get("sea_state_code"),
        "sea_state_category": analysis.get("sea_state_category", "UNKNOWN"),
        "rule_standard": analysis.get("rule_standard", "WMO Code Table 3700 / Douglas Sea Scale"),
        "advisory": advisory_text,
        "generation_mode": mode,
    }
    structured_output: dict[str, Any] = {
        "agent_name": "ORCA Marine Intelligence Agent",
        "workflow_id": f"orca-wf-{uuid4().hex[:12]}",
        "status": result_status,
        "location": {
            "location_name": location_name,
            "requested_latitude": lat,
            "requested_longitude": lon,
            "grid_latitude": grid_lat,
            "grid_longitude": grid_lon,
        },
        "measurements": {
            "variable": "wave_height",
            "unit": "m",
            "sample_count": measurements.get("sample_count", 0),
            "min_wave_height_m": measurements.get("min_wave_height_m"),
            "max_wave_height_m": measurements.get("max_wave_height_m"),
            "avg_wave_height_m": measurements.get("avg_wave_height_m"),
            "latest_wave_height_m": measurements.get("latest_wave_height_m"),
            "timeseries": measurements.get("timeseries", []),
        },
        "units": {"wave_height": "m"},
        "timestamps": {
            "retrieved_at": retrieved_at_iso,
            "forecast_start": forecast_start,
            "forecast_end": forecast_end,
            "forecast_time_window_hours": window,
        },
        "source": {
            "provider": provider.provider_name,
            "model_timezone": "GMT",
            "attribution": "Open-Meteo Marine Weather API (ECMWF / Meteo-France models)",
            "citation": "WMO Code Table 3700 / Douglas Sea Scale; Open-Meteo Marine API (https://open-meteo.com/)",
        },
        "validation_status": {
            "status": result_status,
            "is_valid": result_status == "valid",
            "issues": issues,
            "quality_flags": quality_flags,
            "records_analyzed": len(records),
        },
        "analysis": analysis_payload,
        "limitations": DISCLAIMERS_AND_LIMITATIONS,
        "step_progress": progress,
    }
    return {
        "advisory": advisory_text,
        "summary": advisory_text,
        "limitations": DISCLAIMERS_AND_LIMITATIONS,
        "structured_output": structured_output,
        "step_progress": progress,
    }
# Build LangGraph workflow
builder: StateGraph = StateGraph(MarineState)
builder.add_node("validate_input", validate_input_node)
builder.add_node("collect_marine_data", collect_marine_data)
builder.add_node("normalize_and_validate", normalize_and_validate_evidence)
builder.add_node("analyze_wave_conditions", analyze_wave_conditions)
builder.add_node("generate_advisory_report", generate_advisory_report)
builder.add_edge(START, "validate_input")
builder.add_edge("validate_input", "collect_marine_data")
builder.add_edge("collect_marine_data", "normalize_and_validate")
builder.add_edge("normalize_and_validate", "analyze_wave_conditions")
builder.add_edge("analyze_wave_conditions", "generate_advisory_report")
builder.add_edge("generate_advisory_report", END)
marine_graph = builder.compile()
async def run_marine_workflow(
    *,
    latitude: float,
    longitude: float,
    location_name: str = "Offshore Marine Location",
    forecast_time_window_hours: int = 24,
) -> MarineState:
    """Run the single ORCA Marine Intelligence Agent workflow."""
    if not -90 <= latitude <= 90:
        raise ValueError("latitude must be between -90 and 90")
    if not -180 <= longitude <= 180:
        raise ValueError("longitude must be between -180 and 180")
    initial_state: MarineState = {
        "location_name": location_name,
        "latitude": latitude,
        "longitude": longitude,
        "forecast_time_window_hours": forecast_time_window_hours,
        "step_progress": [],
        "evidence": [],
        "issues": [],
    }
    return cast(MarineState, await marine_graph.ainvoke(initial_state))
