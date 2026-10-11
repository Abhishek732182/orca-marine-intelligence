# ORCA — Marine Intelligence Agent

ORCA is an evidence-grounded AI agent for marine decision support built with Python, FastAPI, and LangGraph.

The system features the **ORCA Marine Intelligence Agent**, which fetches live oceanographic forecasts from Open-Meteo Marine API, verifies evidence quality, maps wave conditions to documented World Meteorological Organization (WMO) sea-state standards, and synthesizes structured marine advisories with strict reliability guarantees.

---

## Architecture: One Agent, One LangGraph Workflow

The **ORCA Marine Intelligence Agent** executes as a single LangGraph stateful graph (`StateGraph(MarineState)`):

```
START 
  ↓
[Step 1: validate_input]          → Validates coordinates (-90..90, -180..180) and forecast window (1..168h)
  ↓
[Step 2: collect_marine_data]     → Fetches live wave heights from Open-Meteo Marine API
  ↓
[Step 3: normalize_and_validate]  → Normalizes evidence, validates timestamps/status, records provenance
  ↓
[Step 4: analyze_wave_conditions] → Computes metrics (min, max, avg, latest) and classifies via WMO Code 3700
  ↓
[Step 5: generate_advisory_report]→ Generates grounded advisory (LLM if configured, deterministic fallback)
  ↓
END
```

### Standards & Reliability
- **Documented Rules Only**: Wave conditions are classified using **WMO Code Table 3700 / Douglas Sea Scale** (WMO-No. 306). No arbitrary thresholds.
- **Strict Evidence Grounding**: Never converts missing data to zero; never hallucinates safety clearances or official warnings.
- **Explicit Limitations**: Acknowledges that wave height alone cannot determine fishing or vessel safety. Wind velocity, swell period, currents, and vessel seaworthiness are required.
- **Graceful Degeneration**: If coordinates are on land or provider data is missing, explicitly returns `UNKNOWN / INCOMPLETE` and `insufficient_evidence`.

---

## Getting Started

### 1. Run the Test Suite
```bash
.venv\Scripts\pytest -v
```
*(All 36 tests pass across evidence schemas, validation, Open-Meteo integration, LangGraph workflow, and REST API)*

### 2. Run the Interactive Terminal Demo
```bash
.venv\Scripts\python scripts/demo_orca_agent.py
```
Or run non-interactively with specific coordinates:
```bash
# Live Offshore Arabian Sea (Goa)
.venv\Scripts\python scripts/demo_orca_agent.py --non-interactive --lat 15.0 --lon 72.0 --location "Offshore Arabian Sea"

# Land Coordinate Demonstration (Shows graceful handling of missing sea data)
.venv\Scripts\python scripts/demo_orca_agent.py --non-interactive --lat 21.15 --lon 79.09 --location "Inland Nagpur"
```

### 3. Start the FastAPI Application
```bash
.venv\Scripts\uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive Swagger docs: `http://127.0.0.1:8000/docs`

### 4. API Endpoints
- `POST /api/orca/analyze`: Invokes the ORCA Marine Intelligence Agent workflow.
- `GET /api/marine/wave-height`: Direct provider wave-height endpoint.
- `GET /health` and `GET /api/health`: Service health check.

#### Example API Request:
```bash
curl -X POST http://127.0.0.1:8000/api/orca/analyze \
  -H "Content-Type: application/json" \
  -d '{"location_name": "Offshore Goa", "latitude": 15.0, "longitude": 72.0, "forecast_time_window_hours": 24}'
```
