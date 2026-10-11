import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
backend_dir = str(PROJECT_ROOT / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

payload = {
    "location_name": "Offshore Arabian Sea (Goa)",
    "latitude": 15.0,
    "longitude": 72.0,
    "forecast_time_window_hours": 24,
}

print("Executing live POST /api/orca/analyze against Open-Meteo...")
response = client.post("/api/orca/analyze", json=payload)
assert response.status_code == 200, f"Expected 200, got {response.status_code}"

data = response.json()

# 1. Verification of measurements & full 24-record forecast
sample_count = data["measurements"]["sample_count"]
timeseries = data["measurements"]["timeseries"]
timeseries_len = len(timeseries)
assert sample_count == 24, f"Expected 24 samples, got {sample_count}"
assert timeseries_len == 24, f"Expected 24 timeseries points, got {timeseries_len}"

# 2. Verification of coordinates
req_lat = data["location"]["requested_latitude"]
req_lon = data["location"]["requested_longitude"]
grid_lat = data["location"]["grid_latitude"]
grid_lon = data["location"]["grid_longitude"]
assert req_lat == 15.0, f"Invalid requested_lat: {req_lat}"
assert req_lon == 72.0, f"Invalid requested_lon: {req_lon}"
assert grid_lat is not None, "grid_latitude is None"
assert grid_lon is not None, "grid_longitude is None"

# 3. Verification of timestamps
retrieved_at = data["timestamps"]["retrieved_at"]
fc_start = data["timestamps"]["forecast_start"]
fc_end = data["timestamps"]["forecast_end"]
assert retrieved_at is not None, "retrieved_at is missing"
assert fc_start is not None, "forecast_start is missing"
assert fc_end is not None, "forecast_end is missing"

# 4. Verification of source attribution
provider = data["source"]["provider"]
attribution = data["source"]["attribution"]
citation = data["source"]["citation"]
assert provider == "open-meteo-marine", f"Unexpected provider: {provider}"
assert "Open-Meteo Marine Weather API" in attribution, f"Unexpected attribution: {attribution}"
assert "WMO Code Table 3700" in citation, f"Unexpected citation: {citation}"

# 5. Save artifacts to data/
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)

sample_file = data_dir / "sample_orca_response.json"
with open(sample_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

trace_file = data_dir / "demo_execution_trace.txt"
with open(trace_file, "w", encoding="utf-8") as f:
    f.write("ORCA MARINE INTELLIGENCE AGENT - DEMO EXECUTION TRACE\n")
    f.write("=" * 75 + "\n\n")
    f.write(f"Target Location:      {data['location']['location_name']}\n")
    f.write(f"Requested Lat/Lon:    {req_lat} deg N, {req_lon} deg E\n")
    f.write(f"Resolved Grid Point:  {grid_lat} deg N, {grid_lon} deg E\n")
    f.write(f"Workflow ID:          {data['workflow_id']}\n")
    f.write(f"Execution Status:     {data['status'].upper()}\n\n")
    f.write("WORKFLOW STEP EXECUTION TRACE:\n")
    for step in data["step_progress"]:
        f.write(f"  {step}\n")
    f.write("\nMEASUREMENTS SUMMARY:\n")
    f.write(f"  Sample Count:         {sample_count} hourly records\n")
    f.write(f"  Min Wave Height:      {data['measurements']['min_wave_height_m']} m\n")
    f.write(f"  Max Wave Height:      {data['measurements']['max_wave_height_m']} m\n")
    f.write(f"  Average Wave Height:  {data['measurements']['avg_wave_height_m']} m\n")
    f.write(f"  Latest Wave Height:   {data['measurements']['latest_wave_height_m']} m\n")
    f.write(f"  Measurement Unit:     {data['units']['wave_height']}\n\n")
    f.write("WMO SEA STATE CLASSIFICATION:\n")
    f.write(f"  WMO Code:             Code {data['analysis']['sea_state_code']}\n")
    f.write(f"  Sea State Category:   {data['analysis']['sea_state_category']}\n")
    f.write(f"  Standard Reference:   {data['analysis']['rule_standard']}\n")
    f.write(f"  Synthesis Mode:       {data['analysis']['generation_mode'].upper()}\n\n")
    f.write("FINAL ADVISORY:\n")
    f.write(f"  {data['analysis']['advisory']}\n\n")
    f.write("SOURCE ATTRIBUTION & PROVENANCE:\n")
    f.write(f"  Provider Name:        {provider}\n")
    f.write(f"  Model Attribution:    {attribution}\n")
    f.write(f"  Standard Citation:    {citation}\n")
    f.write(f"  Provider Timezone:    {data['source']['model_timezone']}\n\n")
    f.write("TIMESTAMPS & WINDOW:\n")
    f.write(f"  Evidence Retrieved At:{retrieved_at}\n")
    f.write(f"  Forecast Start:       {fc_start}\n")
    f.write(f"  Forecast End:         {fc_end}\n")
    f.write(f"  Forecast Window:      {data['timestamps']['forecast_time_window_hours']} Hours\n\n")
    f.write("FULL 24-HOUR FORECAST TIME SERIES:\n")
    for idx, pt in enumerate(timeseries, 1):
        f.write(f"  [{idx:02d}] {pt['timestamp']} -> {pt['wave_height']} m\n")
    f.write("\nOPERATIONAL LIMITATIONS & DISCLAIMERS:\n")
    for idx, lim in enumerate(data["limitations"], 1):
        f.write(f"  [{idx}] {lim}\n")

print("\n--- VERIFICATION PASSED ---")
print(f"Sample response saved: {sample_file}")
print(f"Execution trace saved: {trace_file}")
print(f"Sample count confirmed: {sample_count} / 24")
print(f"Timeseries length confirmed: {timeseries_len} / 24")
print(f"Requested Coordinates: {req_lat} deg N, {req_lon} deg E")
print(f"Resolved Grid Coordinates: {grid_lat} deg N, {grid_lon} deg E")
print(f"Forecast Time Window: {fc_start} to {fc_end}")
print(f"WMO Classification: Code {data['analysis']['sea_state_code']} ({data['analysis']['sea_state_category']})")
print(f"Advisory: {data['analysis']['advisory']}")
