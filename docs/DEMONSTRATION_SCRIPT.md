# ORCA Platform — Reproducible Demonstration Guide (v4.0)

This demonstration guide provides reproducible steps for evaluation committees, examiners, and domain evaluators. It covers the core architectural and scientific principles of ORCA through both browser UI steps and exact curl / PowerShell HTTP commands.

---

## Architectural Overview (College Project Defense)

ORCA is structured into decoupled, evidence-grounded layers:

1. **React Frontend (Port 5173):** Modern, interactive user workspace featuring Leaflet/SVG maritime charts, specialist agent query panels, execution logs, and an AI chat assistant.
2. **FastAPI Backend (Port 8001 / 8010):** High-throughput asynchronous REST API managing telemetry ingestion, Pydantic schema validation, and error propagation.
3. **LangGraph Master Orchestrator:** Dynamic multi-agent planning engine that synthesizes inputs, delegates to specialists concurrently (`asyncio.gather`), reconciles cross-agent telemetry, and detects observation discrepancies.
4. **Decoupled Specialist Agents:**
   - *Weather Agent:* Atmospheric parameters (wind speed/direction, gusts, air temp, WMO precipitation).
   - *Ocean Agent:* Oceanographic parameters (wave height, period, swell, Douglas Sea Scale).
   - *Fishing Zone Agent:* Environmental suitability with strict isolation of biological fish distributions.
   - *Route Agent:* Great-Circle geodesic distance estimation with non-navigable disclaimers.
   - *Safety/Risk Agent:* Deterministic, rule-based maritime risk classification.
5. **Evidence Validation & Plausibility:** Validates physical bounds (e.g. wave height 0–30m, SST -2–45°C), evaluates data freshness, and rejects out-of-bounds coordinates with HTTP 422.
6. **Deterministic Risk Assessment:** Operational safety is computed deterministically from craft limits and WMO thresholds. Favorable wave conditions evaluate craft limits only and **never** clear vessel safety or infer fish presence.

---

## Pre-Demonstration Setup

### 1. Start Backend API
```powershell
cd D:\orca\backend
..\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8001
```
*(Alternatively on port 8010: `..\.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8010` with matching `VITE_ORCA_API_URL`)*

### 2. Start Frontend Web Client
```powershell
cd D:\orca\frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Open Google Chrome to: `http://127.0.0.1:5173/`. Verify the navbar status displays `API: ONLINE`.

---

## Scenario 1: Normal Offshore Marine Analysis

**Objective:** Demonstrate normal data acquisition, WMO sea-state classification, and atmospheric telemetry off the coast of Goa.

### UI Action:
1. Navigate to **Specialist Agents** $\rightarrow$ **1. Weather Agent**.
2. Click preset: **Arabian Sea (15.0, 72.0)** and click **Analyze Weather**.
3. Navigate to **Specialist Agents** $\rightarrow$ **2. Ocean Agent**.
4. Click preset: **Offshore Goa (15.0, 72.0)** and click **Analyze Ocean Conditions**.
5. Observe: Real live-provider marine forecast (values vary with live conditions, e.g. wave height ~0.8 – 1.8 m, WMO Douglas Sea Scale 2–3, ambient sea/air temperatures, and wind speed).

### Exact CLI Reproduction:
```bash
# Weather Agent
curl -s -X POST http://127.0.0.1:8001/api/agents/weather/analyze \
  -H "Content-Type: application/json" \
  -d '{"latitude": 15.0, "longitude": 72.0, "location_name": "Offshore Goa", "forecast_days": 1}'

# Ocean Agent
curl -s -X POST http://127.0.0.1:8001/api/agents/ocean/analyze \
  -H "Content-Type: application/json" \
  -d '{"latitude": 15.0, "longitude": 72.0, "forecast_time_window_hours": 24}'
```
*Expected Result:* HTTP 200 OK with `status: "success"` containing live Open-Meteo telemetry (exact numbers fluctuate with active real-world forecasts).

---

## Scenario 2: Inland Coordinates with Insufficient Evidence

**Objective:** Verify that terrestrial land coordinates return explicit insufficient evidence and never fabricate calm or zero sea conditions.

### UI Action:
1. Navigate to **Specialist Agents** $\rightarrow$ **2. Ocean Agent**.
2. Click preset: **Inland Nagpur (Land Test: 21.15, 79.09)** and click **Analyze Ocean Conditions**.
3. Observe: Status is `insufficient_evidence`, `sample_count: 0`, and notice displays: *"Terrestrial coordinates outside ocean numerical grid."*
4. In **5. Safety/Risk Agent**, run the same coordinates. Risk evaluates to `UNKNOWN / INSUFFICIENT EVIDENCE`, never `LOW` or `SAFE`.

### Exact CLI Reproduction:
```bash
curl -s -X POST http://127.0.0.1:8001/api/agents/ocean/analyze \
  -H "Content-Type: application/json" \
  -d '{"latitude": 21.15, "longitude": 79.09, "location_name": "Inland Nagpur"}'
```
*Expected Result:* HTTP 200 OK with `status: "insufficient_evidence"`, `sample_count: 0`, `avg_wave_height_m: null`.

---

## Scenario 3: Targeted versus Full Specialist Dispatch

**Objective:** Demonstrate dynamic LangGraph planning by requesting a narrow weather check versus a full multi-specialist mission dispatch.

### UI Action:
1. Navigate to **AI Workspace Assistant (Agent 6)**.
2. In the chat composer, type:
   `"Analyze atmospheric weather and wind at 15.0, 72.0"`
   *Result:* Planner dispatches only the Weather specialist (`invoke_weather_agent`).
3. Now type:
   `"Provide comprehensive mission intelligence from Goa (15.0, 72.0) to Mumbai (18.9, 72.8) for small craft fishing mackerel"`
   *Result:* Planner dispatches all specialists concurrently (`Weather`, `Ocean`, `Fishing Zone`, `Route`, `Safety/Risk`).

### Exact CLI Reproduction:
```bash
# Targeted delegation (objective="weather")
curl -s -X POST http://127.0.0.1:8001/api/agents/orchestrator/analyze \
  -H "Content-Type: application/json" \
  -d '{"latitude": 15.0, "longitude": 72.0, "user_objective": "weather"}'

# Full dispatch (objective="all")
curl -s -X POST http://127.0.0.1:8001/api/agents/orchestrator/analyze \
  -H "Content-Type: application/json" \
  -d '{"origin_latitude": 15.0, "origin_longitude": 72.0, "destination_latitude": 18.9, "destination_longitude": 72.8, "user_objective": "all", "vessel_type": "small_craft", "target_species": "Mackerel"}'
```
*Expected Result:* Targeted request plans subset of agents; full dispatch executes all 5 specialists concurrently.

---

## Scenario 4: Conflicting Environmental Evidence

**Objective:** Verify that when sensor observations conflict (e.g., high wave height with mild wind or discordant WMO codes), raw telemetry is preserved and discrepancy warnings are raised without data corruption.

### UI Action:
1. Navigate to **Specialist Agents** $\rightarrow$ **5. Safety/Risk Agent**.
2. Supply conflicting observations: Wave height `3.8 m` with Wind speed `12.0 kts`.
3. Observe: Warning is flagged, risk category reflects the hazardous $3.8\text{ m}$ sea state (`CRITICAL` or `HIGH`), and raw values remain intact.

### Exact CLI Reproduction:
```bash
curl -s -X POST http://127.0.0.1:8001/api/agents/orchestrator/analyze \
  -H "Content-Type: application/json" \
  -d '{"latitude": 15.0, "longitude": 72.0, "wave_height_m": 3.8, "wind_speed_knots": 12.0, "user_objective": "safety_check"}'
```
*Expected Result:* HTTP 200 OK with `warnings` containing discrepancy notice and risk escalated to `CRITICAL`.

---

## Scenario 5: Critical-Risk Escalation & Hazardous Waves

**Objective:** Confirm that hazardous conditions unconditionally escalate risk and emit emergency directives that cannot be overridden, verifiable via both simulated extremes and real live high-sea storm coordinates.

### UI Action (Simulation):
1. In **5. Safety/Risk Agent**, click button: **Simulate Severe Gale (Hs=3.8m, 38kts Wind)**.
2. Click **Invoke Safety/Risk Agent**.
3. Observe: Badge turns red `CRITICAL`, and recommendations prominently feature `DANGER: Suspend all operations immediately. Seek harbor protection.`

### CLI Reproduction (Simulated Severe Gale):
```bash
curl -s -X POST http://127.0.0.1:8001/api/agents/safety-risk/analyze \
  -H "Content-Type: application/json" \
  -d '{"latitude": 15.0, "longitude": 72.0, "vessel_type": "small_craft", "wave_height_m": 3.8, "wind_speed_knots": 38.0}'
```
*Expected Result:* HTTP 200 OK with `risk_category: "CRITICAL"` and `recommendations` containing `DANGER`.

### CLI Reproduction (Live High-Sea Hazardous Waves — Roaring Forties: -52.0, 75.0):
```bash
curl -s -X POST http://127.0.0.1:8001/api/agents/fishing-zone/analyze \
  -H "Content-Type: application/json" \
  -d '{"latitude": -52.0, "longitude": 75.0, "location_name": "Southern Ocean Storm Track"}'
```
*Expected Result:* HTTP 200 OK with `operational_feasibility: "HAZARDOUS"`, live wave height $\ge 4.0\text{ m}$, and sea state category `"Rough"` or `"Very rough"`.

---

## Scenario 6: Environmental Suitability versus Biological Prediction Safeguards

**Objective:** Demonstrate scientific separation between physical wave feasibility and unverified biological presence, verifying strict preservation of production safeguards without a trained model or authorized ground truth.

### UI Action:
1. Navigate to **Specialist Agents** $\rightarrow$ **3. Fishing Zone Agent**.
2. Enter: Latitude `15.0`, Longitude `72.0`, Species `Mackerel`.
3. Click **Analyze Fishing Zone & Suitability**.
4. Inspect result:
   - `Operational Feasibility`: **`FAVORABLE`** (calm waves permit vessel operation).
   - `Verified Fish Distribution`: **`UNVERIFIED`** (direct fish location telemetry unavailable).
   - `Catch Probability`: **`null`** (never invented).
   - `Biomass Prediction`: **`null`** (never estimated from environmental proxies).
   - `Predictive Accuracy`: **`NOT_EVALUABLE`**.
   - Notice: *"Vessel Safety Grounding: Operational wave feasibility does NOT determine vessel sailing clearance or fish presence."*

### Exact CLI Reproduction:
```bash
curl -s -X POST http://127.0.0.1:8001/api/agents/fishing-zone/analyze \
  -H "Content-Type: application/json" \
  -d '{"latitude": 15.0, "longitude": 72.0, "target_species": "Mackerel"}'
```
*Expected Result:* HTTP 200 OK with:
- `operational_feasibility: "FAVORABLE"`
- `operational_feasibility_scope: "STRICTLY_PHYSICAL_WAVE_CONDITIONS"`
- `analysis.biological_prediction.fish_presence: "UNVERIFIED"`
- `analysis.biological_prediction.catch_probability: null`
- `analysis.biological_prediction.biomass_prediction: null`
- `analysis.biological_prediction.predictive_accuracy: "NOT_EVALUABLE"`
- `analysis.biological_prediction.ground_truth_status: "AWAITING_AUTHORIZED_DATA"`

---

## Summary of Scientific Boundaries & Disclaimers

1. **Strict Biological Invariants:** In the absence of a validated biological model and authorized institutional ground truth (e.g. ICAR-CMFRI), catch probability remains `null`, fish presence is `UNVERIFIED`, and prediction accuracy is `NOT_EVALUABLE`.
2. **Decoupled Craft Feasibility vs. Sailing Clearance:** Favorable wave conditions indicate physical craft tolerance only; they **never** grant maritime safety clearance or imply fish presence.
3. **Geodesic Route Disclaimers:** All routes are Great-Circle geodesic distance estimates and must **never** be treated as certified navigational passage plans.
4. **Safety Primacy:** Terrestrial inland coordinates or absent sensor telemetry are strictly evaluated as `UNKNOWN / INSUFFICIENT EVIDENCE`, never presumed safe.
