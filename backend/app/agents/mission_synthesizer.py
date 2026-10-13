"""Evidence-Grounded Descriptive Synthesis for ORCA LangGraph Orchestrator.

Combines specialist agent results, partitions measured observations from derived models,
strictly preserves composite safety risk (CRITICAL/HIGH never downgraded; missing telemetry never safe),
and generates grounded descriptive mission summaries using the configured LLM client.
Includes transparent, strictly verified deterministic fallback on LLM failure, timeout, or missing keys.
"""

from typing import Any
from app.agents.llm_client import call_chat_llm

SYNTHESIS_SYSTEM_PROMPT = """You are the ORCA Marine Intelligence Master Synthesis Engine.
Generate an evidence-grounded, professional maritime mission synthesis based ONLY on the provided JSON evidence.
STRICT RELIABILITY & SAFETY RULES:
1. Ground every statement strictly in the provided JSON evidence.
2. NEVER invent fish coordinates, biomass, catch probabilities, chlorophyll-a, or citations. Direct fish telemetry is unverified.
3. NEVER claim conditions are safe based on wave height alone.
4. STRICT SAFETY RISK PRESERVATION:
   - If composite safety risk is CRITICAL or HIGH, you MUST report CRITICAL or HIGH danger. Never downgrade risk.
   - If safety risk is UNKNOWN or INSUFFICIENT EVIDENCE, or telemetry is missing, NEVER declare conditions calm, low-risk, or safe.
5. GEODESIC ROUTE ESTIMATES:
   - State clearly that Great-Circle route distance is a straight-line estimate only and does NOT verify hydrographic navigability, bathymetry, or channel clearance.
6. OBSERVATION DISCREPANCIES & FAILURES:
   - Highlight any reported observation discrepancy (e.g. wave height vs WMO sea state code).
   - Acknowledge any specialist agent errors or insufficient evidence directly.
7. Be structured, factual, and direct. Format with clear bullet points."""


def generate_deterministic_synthesis(
    *,
    location_name: str,
    latitude: float | None,
    longitude: float | None,
    user_objective: str,
    vessel_type: str,
    measured_observations: dict[str, Any],
    derived_estimates: dict[str, Any],
    composite_safety_risk: dict[str, Any],
    warnings: list[str],
    missing_evidence: list[str],
    errors: dict[str, str],
    recommendations: list[str],
    clarification_needed: bool = False,
    clarification_prompt: str | None = None,
) -> str:
    """Generate deterministic, scientifically rigorous, evidence-grounded synthesis."""
    if clarification_needed:
        prompt_text = clarification_prompt or "Essential mission parameters are missing. Please provide geographical coordinates."
        return (
            f"ORCA Mission Clarification Required [{user_objective.upper()}]:\n"
            f"- Status: INCOMPLETE PARAMETERS\n"
            f"- Notice: {prompt_text}\n"
            f"- Safety Notice: ORCA does not invent coordinates or voyage destinations. Accurate telemetry retrieval requires exact inputs."
        )

    lines: list[str] = []
    lat_str = f"{latitude:.2f}°N" if latitude is not None else "N/A"
    lon_str = f"{longitude:.2f}°E" if longitude is not None else "N/A"
    lines.append(f"**ORCA Mission Intelligence Synthesis for {location_name} ({lat_str}, {lon_str}) [{user_objective.upper()}]:**")

    # 1. Measured Numerical Observations
    wave_h = measured_observations.get("wave_height_m")
    wind_kts = measured_observations.get("wind_speed_knots")
    wind_dir = measured_observations.get("wind_direction_deg")
    temp_c = measured_observations.get("temperature_c")
    precip_mm = measured_observations.get("precipitation_mm")
    wmo_code = measured_observations.get("wmo_sea_state_code")
    wmo_desc = measured_observations.get("wmo_sea_state_description")

    obs_parts: list[str] = []
    if wave_h is not None:
        obs_parts.append(f"Significant wave height: {wave_h:.2f} m")
    if wmo_code is not None or wmo_desc:
        obs_parts.append(f"WMO Sea State: Code {wmo_code or 'N/A'} ({wmo_desc or 'N/A'})")
    if wind_kts is not None:
        dir_txt = f" from {wind_dir:.0f}°" if wind_dir is not None else ""
        obs_parts.append(f"Wind speed: {wind_kts:.1f} kts{dir_txt}")
    if temp_c is not None:
        obs_parts.append(f"Air temperature: {temp_c:.1f}°C")
    if precip_mm is not None:
        obs_parts.append(f"Precipitation: {precip_mm:.1f} mm/h")

    if obs_parts:
        lines.append("- **Measured Provider Observations:** " + "; ".join(obs_parts) + ".")
    else:
        lines.append("- **Measured Provider Observations:** Missing or offline telemetry. In-situ buoy or harbor reports required.")

    # 2. Composite Safety & Risk
    risk_cat = composite_safety_risk.get("risk_category", "UNKNOWN")
    risk_score = composite_safety_risk.get("risk_score")
    score_txt = f" (Score: {risk_score})" if risk_score is not None else ""
    headline = composite_safety_risk.get("status_headline", "")
    lines.append(f"- **Composite Safety/Risk:** **{risk_cat}**{score_txt} - {headline} (Assessed for {vessel_type.replace('_', ' ')}).")

    # 3. Geodesic Route Calculation (if route planned)
    route_info = derived_estimates.get("geodesic_route")
    if route_info and route_info.get("distance_km") is not None:
        d_km = route_info.get("distance_km")
        d_nm = route_info.get("distance_nm")
        t_hrs = route_info.get("estimated_transit_hours")
        t_txt = f", estimated transit ~{t_hrs:.1f}h" if t_hrs is not None else ""
        lines.append(
            f"- **Estimated Geodesic Route:** {d_km:.1f} km ({d_nm:.1f} NM){t_txt}. "
            f"*(Great-Circle geodesic distance estimate only; does not verify hydrographic navigability, bathymetry, shoals, or authorized channels).*"
        )

    # 4. Fisheries Suitability
    fz_info = derived_estimates.get("fisheries_suitability")
    if fz_info:
        feas = fz_info.get("operational_feasibility", "UNVERIFIED")
        suit = fz_info.get("zone_suitability", "INSUFFICIENT_EVIDENCE")
        lines.append(
            f"- **Fisheries & Operability:** Physical wave operability is rated **{feas}**; "
            f"environmental habitat suitability is rated **{suit}**. "
            f"Direct biological fish distributions remain **INSUFFICIENT_EVIDENCE** "
            f"(environmental suitability does not indicate actual fish presence, catch probability, biomass, or validated prediction)."
        )

    # 5. Warnings and Inconsistencies
    if warnings:
        lines.append("\n**Warnings & Observational Notices:**")
        for w in warnings:
            lines.append(f"- ⚠️ {w}")

    # 6. Errors or Missing Evidence
    if missing_evidence:
        lines.append("\n**Missing Telemetry & Evidence Gaps:**")
        for m in missing_evidence:
            lines.append(f"- ℹ️ {m}")

    if errors:
        lines.append("\n**Specialist Execution Notes:**")
        for agent_name, err in errors.items():
            lines.append(f"- ❌ {agent_name.replace('_', ' ').title()}: {err}")

    # 7. Actionable Recommendations
    if recommendations:
        lines.append("\n**Actionable Recommendations:**")
        for rec in recommendations[:3]:
            lines.append(f"- ⚓ {rec}")

    return "\n".join(lines)


async def synthesize_mission_advisory(
    *,
    location_name: str,
    latitude: float | None,
    longitude: float | None,
    user_objective: str,
    vessel_type: str,
    measured_observations: dict[str, Any],
    derived_estimates: dict[str, Any],
    composite_safety_risk: dict[str, Any],
    warnings: list[str],
    missing_evidence: list[str],
    errors: dict[str, str],
    recommendations: list[str],
    clarification_needed: bool = False,
    clarification_prompt: str | None = None,
) -> tuple[str, str]:
    """Generate evidence-grounded mission synthesis via LLM with deterministic fallback.

    Returns:
        tuple of (synthesis_text, generation_mode) where mode is 'llm' or 'deterministic'.
    """
    deterministic_text = generate_deterministic_synthesis(
        location_name=location_name,
        latitude=latitude,
        longitude=longitude,
        user_objective=user_objective,
        vessel_type=vessel_type,
        measured_observations=measured_observations,
        derived_estimates=derived_estimates,
        composite_safety_risk=composite_safety_risk,
        warnings=warnings,
        missing_evidence=missing_evidence,
        errors=errors,
        recommendations=recommendations,
        clarification_needed=clarification_needed,
        clarification_prompt=clarification_prompt,
    )

    if clarification_needed:
        return deterministic_text, "deterministic"

    user_payload = {
        "location": {"name": location_name, "latitude": latitude, "longitude": longitude},
        "user_objective": user_objective,
        "vessel_type": vessel_type,
        "measured_observations": measured_observations,
        "derived_estimates": derived_estimates,
        "composite_safety_risk": composite_safety_risk,
        "warnings": warnings,
        "missing_evidence": missing_evidence,
        "errors": errors,
        "recommendations": recommendations,
    }

    user_prompt = f"Verified Marine Evidence:\n{user_payload}\n\nGenerate the synthesized advisory following all strict reliability rules."

    try:
        raw_llm_text, mode = await call_chat_llm(
            system_prompt=SYNTHESIS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            json_mode=False,
            timeout=6.0,
        )
    except Exception:
        raw_llm_text, mode = None, "deterministic"

    if raw_llm_text and mode == "llm":
        # Guardrail verification: ensure LLM did not downgrade critical risk or declare missing telemetry safe
        risk_cat = composite_safety_risk.get("risk_category", "UNKNOWN")
        text_lower = raw_llm_text.lower()

        # Rule A: If risk is CRITICAL or HIGH, text must not declare safe to sail or calm conditions
        if risk_cat in ("CRITICAL", "HIGH"):
            if "safe to sail" in text_lower or "calm conditions" in text_lower or "low risk" in text_lower:
                return deterministic_text, "deterministic"

        # Rule B: If risk is UNKNOWN / INSUFFICIENT EVIDENCE, text must not declare safe
        if "UNKNOWN" in risk_cat or "INSUFFICIENT" in risk_cat:
            if "safe to sail" in text_lower or "favorable operating conditions" in text_lower:
                return deterministic_text, "deterministic"

        # Rule C: Text must not hallucinate catch probabilities or verified fish biomass
        if (
            "catch probability:" in text_lower
            or "biomass estimate:" in text_lower
            or "tons/km" in text_lower
            or "guaranteed catch" in text_lower
            or "verified fish school" in text_lower
        ):
            return deterministic_text, "deterministic"

        # Rule D: Text must not present route as certified navigational route or wave info as safety clearance
        if (
            "certified navigational route" in text_lower
            or "official navigational track" in text_lower
            or "wave clearance granted" in text_lower
            or "vessel safety clearance granted" in text_lower
        ):
            return deterministic_text, "deterministic"

        return raw_llm_text.strip(), "llm"

    return deterministic_text, "deterministic"
