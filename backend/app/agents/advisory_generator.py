"""Advisory generation for ORCA Marine Intelligence Agent.

Supports LLM-assisted generation when credentials are configured in environment
variables, with an automatic, strictly grounded deterministic fallback.
Never hallucinates safety claims, official warnings, or non-existent data.
"""

import os
from typing import Any
import httpx


SYSTEM_PROMPT = """You are the ORCA Marine Intelligence Agent.
Generate a concise, factual advisory based ONLY on the provided marine evidence.
STRICT RELIABILITY RULES:
1. Never claim that fishing, navigation, or sailing is safe based on wave height alone.
2. Wave height is only one marine factor; wind, currents, swell period, and vessel seaworthiness are required.
3. State the WMO sea state category and the wave height range accurately.
4. Keep the summary under 4 sentences. Be professional, direct, and evidence-grounded."""


def generate_deterministic_advisory(
    *,
    location_name: str,
    latitude: float,
    longitude: float,
    forecast_time_window_hours: int,
    result_status: str,
    measurements: dict[str, Any],
    sea_state: dict[str, Any],
    issues: list[str],
) -> str:
    """Generate a deterministic, scientifically grounded advisory."""
    if result_status == "insufficient_evidence" or measurements.get("sample_count", 0) == 0:
        issue_detail = f" Issues noted: {', '.join(issues)}." if issues else ""
        return (
            f"Advisory: UNKNOWN / INCOMPLETE. No usable wave-height records were returned "
            f"for '{location_name}' ({latitude:.4f} deg N, {longitude:.4f} deg E). "
            f"Marine conditions cannot be determined from this provider.{issue_detail} "
            f"Coordinates may be located on land or outside active numerical sea-grid coverage. "
            f"Independent in-situ observations or local port authority reports are required."
        )

    if result_status == "evidence_requires_review":
        issue_detail = f" Issues noted: {', '.join(issues)}." if issues else ""
        return (
            f"Advisory: CAUTION / EVIDENCE REQUIRES REVIEW. Marine evidence was retrieved for '{location_name}' "
            f"({latitude:.4f} deg N, {longitude:.4f} deg E) but flagged quality issues:{issue_detail} "
            f"Conditions cannot be safely verified from this provider alone. "
            f"Independent observations or local port authority reports are required."
        )

    min_h = measurements.get("min_wave_height_m")
    max_h = measurements.get("max_wave_height_m")
    avg_h = measurements.get("avg_wave_height_m")
    latest_h = measurements.get("latest_wave_height_m")
    wmo_code = sea_state.get("sea_state_code") if sea_state.get("sea_state_code") is not None else sea_state.get("wmo_code")
    category = sea_state.get("sea_state_category") or sea_state.get("category", "UNKNOWN")

    return (
        f"Advisory for {location_name} ({latitude:.4f} deg N, {longitude:.4f} deg E): "
        f"Forecast significant wave heights over the next {forecast_time_window_hours}h "
        f"range from {min_h:.2f} m to {max_h:.2f} m (average {avg_h:.2f} m, latest {latest_h:.2f} m). "
        f"Sea conditions are classified as '{category}' under WMO Code Table 3700 (Sea State Code {wmo_code}). "
        f"Operational Notice: Wave height alone does not constitute a maritime navigation or fishing safety clearance; "
        f"mariners must inspect wind speeds, swell direction, tidal currents, and official hydrographic notices before proceeding."
    )


async def generate_advisory(
    *,
    location_name: str,
    latitude: float,
    longitude: float,
    forecast_time_window_hours: int,
    result_status: str,
    measurements: dict[str, Any],
    sea_state: dict[str, Any],
    issues: list[str],
) -> tuple[str, str]:
    """Generate marine advisory via LLM if configured, otherwise deterministic fallback.

    Returns:
        tuple of (advisory_text, generation_mode) where mode is 'llm' or 'deterministic'.
    """
    if result_status in ("insufficient_evidence", "evidence_requires_review") or measurements.get("sample_count", 0) == 0:
        return (
            generate_deterministic_advisory(
                location_name=location_name,
                latitude=latitude,
                longitude=longitude,
                forecast_time_window_hours=forecast_time_window_hours,
                result_status=result_status,
                measurements=measurements,
                sea_state=sea_state,
                issues=issues,
            ),
            "deterministic",
        )

    # Check for LLM credentials in environment variables
    openai_key = os.environ.get("OPENAI_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")

    if openai_key:
        try:
            user_prompt = (
                f"Location: {location_name} ({latitude} deg N, {longitude} deg E)\n"
                f"Forecast Window: {forecast_time_window_hours} hours\n"
                f"Wave Heights: Min={measurements.get('min_wave_height_m')}m, "
                f"Max={measurements.get('max_wave_height_m')}m, "
                f"Avg={measurements.get('avg_wave_height_m')}m, "
                f"Latest={measurements.get('latest_wave_height_m')}m\n"
                f"WMO Sea State Code: {sea_state.get('wmo_code')} ({sea_state.get('category')})\n"
                f"Generate a concise advisory following all strict reliability rules."
            )
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openai_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.2,
                        "max_tokens": 150,
                    },
                )
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"].strip()
                    if content:
                        return content, "llm"
        except Exception:
            # Fall through cleanly to deterministic fallback
            pass

    elif gemini_key:
        try:
            user_prompt = (
                f"Location: {location_name} ({latitude} deg N, {longitude} deg E)\n"
                f"Forecast Window: {forecast_time_window_hours} hours\n"
                f"Wave Heights: Min={measurements.get('min_wave_height_m')}m, "
                f"Max={measurements.get('max_wave_height_m')}m, "
                f"Avg={measurements.get('avg_wave_height_m')}m\n"
                f"WMO Sea State Code: {sea_state.get('wmo_code')} ({sea_state.get('category')})\n"
                f"Generate a concise advisory."
            )
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.post(
                    url,
                    json={
                        "contents": [
                            {"role": "user", "parts": [{"text": f"{SYSTEM_PROMPT}\n\n{user_prompt}"}]}
                        ]
                    },
                )
                if resp.status_code == 200:
                    candidate = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if candidate:
                        return candidate, "llm"
        except Exception:
            # Fall through cleanly to deterministic fallback
            pass

    # Deterministic fallback
    advisory_text = generate_deterministic_advisory(
        location_name=location_name,
        latitude=latitude,
        longitude=longitude,
        forecast_time_window_hours=forecast_time_window_hours,
        result_status=result_status,
        measurements=measurements,
        sea_state=sea_state,
        issues=issues,
    )
    return advisory_text, "deterministic"

