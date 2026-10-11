"""ORCA Marine Intelligence Agent - Interactive Terminal Demo.

Demonstrates the single LangGraph agent running live against Open-Meteo Marine API,
executing evidence validation, WMO Code Table 3700 sea-state analysis, and
advisory report generation.

Usage:
    python scripts/demo_orca_agent.py
    python scripts/demo_orca_agent.py --non-interactive --lat 15.0 --lon 72.0
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any
from typing_extensions import TypedDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
backend_dir = str(PROJECT_ROOT / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.marine_graph import run_marine_workflow


class PresetLocation(TypedDict):
    name: str
    lat: float
    lon: float
    desc: str


PRESET_LOCATIONS: list[PresetLocation] = [
    {
        "name": "Offshore Arabian Sea (Goa)",
        "lat": 15.0,
        "lon": 72.0,
        "desc": "Open ocean waters ~150km offshore Goa (High reliability marine data)",
    },
    {
        "name": "Offshore Mumbai (Deep Sea)",
        "lat": 18.9,
        "lon": 71.5,
        "desc": "Offshore western continental shelf of India",
    },
    {
        "name": "Bay of Bengal (Offshore Chennai)",
        "lat": 13.1,
        "lon": 80.8,
        "desc": "Offshore eastern coast in the Bay of Bengal",
    },
    {
        "name": "Inland Nagpur (Land Test Coordinate)",
        "lat": 21.15,
        "lon": 79.09,
        "desc": "Demonstrates graceful handling of missing evidence on land",
    },
]


def print_banner():
    banner = r"""
================================================================================
   ___  ____   ____    _      __  __            _             _                    
  / _ \|  _ \ / ___|  / \    |  \/  | __ _ _ __(_)_ __   ___ | |                   
 | | | | |_) | |     / _ \   | |\/| |/ _` | '__| | '_ \ / _ \| |                   
 | |_| |  _ <| |___ / ___ \  | |  | | (_| | |  | | | | |  __/|_|                   
  \___/|_| \_\\____/_/   \_\ |_|  |_|\__,_|_|  |_|_| |_|\___|(_)                   
             MARINE INTELLIGENCE AGENT - EVIDENCE-GROUNDED ADVISORY                
================================================================================
"""
    print(banner)


def prompt_user_selection() -> tuple[str, float, float, int]:
    """Interactively prompt user for location and forecast window."""
    print("Available Test Locations:")
    for idx, loc in enumerate(PRESET_LOCATIONS, 1):
        print(f"  [{idx}] {loc['name']:<35} (Lat: {loc['lat']} deg, Lon: {loc['lon']} deg)")
        print(f"      -> {loc['desc']}")
    print("  [5] Custom Coordinates (Enter your own Lat/Lon)")
    print("-" * 80)

    try:
        choice = input("Select an option [1-5] (Press Enter for [1]): ").strip()
    except (EOFError, KeyboardInterrupt):
        choice = "1"

    if choice == "" or choice == "1":
        selected = PRESET_LOCATIONS[0]
        return selected["name"], selected["lat"], selected["lon"], 24
    elif choice == "2":
        selected = PRESET_LOCATIONS[1]
        return selected["name"], selected["lat"], selected["lon"], 24
    elif choice == "3":
        selected = PRESET_LOCATIONS[2]
        return selected["name"], selected["lat"], selected["lon"], 24
    elif choice == "4":
        selected = PRESET_LOCATIONS[3]
        return selected["name"], selected["lat"], selected["lon"], 24
    elif choice == "5":
        try:
            name_input = input("Enter Location Name [Custom Marine Point]: ").strip()
            loc_name = name_input if name_input else "Custom Marine Point"

            lat_str = input("Enter Latitude (-90 to 90) [15.0]: ").strip()
            lat = float(lat_str) if lat_str else 15.0

            lon_str = input("Enter Longitude (-180 to 180) [72.0]: ").strip()
            lon = float(lon_str) if lon_str else 72.0

            hrs_str = input("Enter Forecast Window in hours (1-168) [24]: ").strip()
            hrs = int(hrs_str) if hrs_str else 24

            return loc_name, lat, lon, hrs
        except ValueError as err:
            print(f"Invalid input ({err}), defaulting to Preset [1].")
            selected = PRESET_LOCATIONS[0]
            return selected["name"], selected["lat"], selected["lon"], 24
    else:
        print("Unrecognized option; defaulting to Preset [1].")
        selected = PRESET_LOCATIONS[0]
        return selected["name"], selected["lat"], selected["lon"], 24


async def run_demo(
    location_name: str,
    latitude: float,
    longitude: float,
    forecast_hours: int,
):
    print("\n" + "=" * 80)
    print(">>> INITIATING ORCA MARINE INTELLIGENCE AGENT")
    print(f"    Target: '{location_name}' | Coordinates: ({latitude:.4f} deg N, {longitude:.4f} deg E)")
    print(f"    Forecast Time Window: {forecast_hours} Hours")
    print("=" * 80)

    print("\n[+] WORKFLOW EXECUTION TRACE:")
    result = await run_marine_workflow(
        latitude=latitude,
        longitude=longitude,
        location_name=location_name,
        forecast_time_window_hours=forecast_hours,
    )

    for step in result.get("step_progress", []):
        print(f"  {step}")

    structured = result.get("structured_output", {})
    status = structured.get("status", "unknown")
    measurements = structured.get("measurements", {})
    analysis = structured.get("analysis", {})
    source = structured.get("source", {})
    validation = structured.get("validation_status", {})
    limitations = structured.get("limitations", [])

    print("\n" + "-" * 80)
    print(">>> AGENT ANALYSIS SUMMARY:")
    print(f"    Status:                 {status.upper()}")
    print(f"    Provider:               {source.get('provider')} ({source.get('attribution')})")
    print(f"    Data Verification:      {'PASSED' if validation.get('is_valid') else 'FLAGGED / INSUFFICIENT'}")
    print(f"    Records Analyzed:       {measurements.get('sample_count', 0)}")

    if measurements.get("sample_count", 0) > 0:
        print(f"    Wave Height Range:      {measurements.get('min_wave_height_m')} m - {measurements.get('max_wave_height_m')} m")
        print(f"    Average Wave Height:    {measurements.get('avg_wave_height_m')} m")
        print(f"    Current Wave Height:    {measurements.get('latest_wave_height_m')} m")
        print(f"    WMO Sea State Code:     Code {analysis.get('sea_state_code')} ({analysis.get('sea_state_category')})")
        print(f"    Rule Standard:          {analysis.get('rule_standard')}")
    else:
        print(f"    Wave Condition Status:  UNKNOWN / INCOMPLETE")
        print(f"    Provider Response:      No valid sea records returned for these coordinates.")

    print(f"    Synthesis Mode:         {analysis.get('generation_mode', 'deterministic').upper()}")

    print("\n" + "=" * 80)
    print("[*] FINAL ADVISORY TEXT:")
    print("=" * 80)
    print(f"{analysis.get('advisory')}")

    print("\n" + "=" * 80)
    print("[!] OPERATIONAL LIMITATIONS & MANDATORY DISCLAIMERS:")
    print("=" * 80)
    for idx, lim in enumerate(limitations, 1):
        print(f"  [{idx}] {lim}")

    if validation.get("issues"):
        print("\n" + "!" * 80)
        print("[!] DETECTED DATA / VALIDATION ISSUES:")
        for issue in validation["issues"]:
            print(f"  * {issue}")
        print("!" * 80)

    print("\n" + "=" * 80)
    print("[#] COMPLETE STRUCTURED JSON OUTPUT:")
    print("=" * 80)
    print(json.dumps(structured, indent=2))
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="ORCA Marine Intelligence Agent Terminal Demo"
    )
    parser.add_argument("--non-interactive", action="store_true", help="Run without prompts")
    parser.add_argument("--lat", type=float, default=15.0, help="Latitude (-90 to 90)")
    parser.add_argument("--lon", type=float, default=72.0, help="Longitude (-180 to 180)")
    parser.add_argument("--location", type=str, default="Offshore Arabian Sea (Goa)", help="Location name")
    parser.add_argument("--hours", type=int, default=24, help="Forecast window in hours")

    args = parser.parse_args()

    print_banner()

    if args.non_interactive:
        loc_name = args.location
        lat = args.lat
        lon = args.lon
        hours = args.hours
    else:
        loc_name, lat, lon, hours = prompt_user_selection()

    asyncio.run(
        run_demo(
            location_name=loc_name,
            latitude=lat,
            longitude=lon,
            forecast_hours=hours,
        )
    )


if __name__ == "__main__":
    main()
