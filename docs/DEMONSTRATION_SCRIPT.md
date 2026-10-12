# ORCA Platform — Five-Minute Live Demonstration Script

This script is structured for technical evaluators, instructors, and maritime domain experts. It demonstrates ORCA's five decoupled specialist agents, the AI Workspace Assistant, the master mission orchestrator, evidence provenance, and scientific safety guarantees.

---

## Pre-Demonstration Setup (1 Minute Before Presentation)

1. **Verify Backend is Running** (Port 8010):
   ```powershell
   cd d:\orca
   .\.venv\Scripts\Activate.ps1
   $env:PYTHONPATH = "d:\orca\backend"
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
   ```
2. **Verify Frontend is Running** (Port 5173):
   ```powershell
   cd d:\orca\frontend
   npm run dev
   ```
3. **Open Browser**: Open Google Chrome to `http://127.0.0.1:5173/`.

---

## Minute 1: System Overview, Design System & API Health Check

### Action
- Point to the top navigation bar. Highlight the green **API: ONLINE** indicator.
- Point out the light-theme design system: crisp white canvas, high-contrast typography, and subtle borders.
- Explain the role of the left sidebar containing the **6-Agent Selector** and navigation modes.

### Spoken Explanation for Evaluators
> *"Welcome to ORCA, an evidence-grounded marine intelligence and fishing advisory platform. 
> Notice the top-right status indicator reading 'API: ONLINE'. The React 19 frontend is communicating with our FastAPI backend on port 8010. 
> ORCA is built on five independent specialist agents, an autonomous workspace assistant, and a master mission orchestrator. 
> The core tenet of ORCA is strict evidence grounding: we never invent fish coordinates, we never fabricate satellite measurements, and we clearly separate physical wave feasibility from vessel sailing clearance."*

---

## Minute 2: AI Workspace Assistant (Agent 6) & Passage Planning

### Action
- In the **AI Workspace Assistant** chat composer at the bottom of the screen, click the preset chip:
  `"Plan geodesic route from Goa (15.0, 72.0) to Mumbai (18.9, 72.8)"`
  or type:
  `"Plan passage from Goa (15.0, 72.0) to Mumbai (18.9, 72.8)"`
- Click **Send**.
- Watch the live execution log in the central panel:
  1. *[Step 1]* Planning mission execution.
  2. *[Step 2]* Dispatching Route Agent tool.
  3. *[Step 3]* Synthesizing mission advisory.
- Show the interactive map on the right updating to draw the 442 km route between Goa and Mumbai.
- Point out the amber **Nautical Navigation Disclaimer** box below the map.

### Spoken Explanation for Evaluators
> *"Here, the AI Workspace Assistant parses the natural language goal and creates a structured 3-step execution plan. 
> It dispatches the Route Agent to compute the Great-Circle geodesic distance—exactly 442 kilometers (241.8 nautical miles). 
> Look at the prominent amber disclaimer: ORCA explicitly marks this as a straight-line mathematical estimate, NOT an authorized hydrographic passage plan. 
> It reminds the mariner that underwater shoals, bathymetric depths, and Traffic Separation Schemes must be verified on official nautical charts before putting to sea."*

---

## Minute 3: Specialist Agent 3 (Fishing Zone Agent) & Evidence Grounding

### Action
- Click **Specialist Agents** in the left sidebar.
- Click **3. Fishing Zone Agent**.
- Enter or verify the coordinates:
  - Latitude: `15.0`
  - Longitude: `72.0`
  - Target Species: `Mackerel`
- Click **Analyze Fishing Zone**.
- Inspect the response card:
  - Status: `INSUFFICIENT_EVIDENCE`
  - Mode: `LIVE OBSERVATIONS` badge (green)
  - Vessel Operability: `FAVORABLE` (wave height ~1.1m)
  - Fisheries Telemetry: `UNVERIFIED`
  - Suitability Score: `N/A` (0% coverage)

### Spoken Explanation for Evaluators
> *"Now we examine Specialist Agent 3: Fishing Zone Agent. 
> Notice that vessel operability is marked FAVORABLE because physical waves are calm at 1.1 meters. 
> However, look at the overall status: it is strictly marked INSUFFICIENT_EVIDENCE, and the suitability score is N/A. 
> This embodies our core scientific guarantee: Open-Meteo provides physical wave physics only. 
> Without direct acoustic fish sonar telemetry or satellite chlorophyll composites, ORCA strictly refuses to fabricate fish presence or generate arbitrary suitability scores. 
> Physical wave feasibility evaluates boat operability only—it does not prove fish exist."*

---

## Minute 4: Specialist Agent 5 (Safety/Risk Agent) & Emergency Gale Simulation

### Action
- Click **5. Safety/Risk Agent** in the agent selector.
- Click the button: **Simulate Severe Gale (42 kts, 4.5m waves)**.
- Observe the immediate response:
  - Risk Level: **CRITICAL RISK** (Blood-red badge)
  - Safety Assessment: **DANGER: Gale force winds exceed small craft survival envelope**
  - Recommendations: Immediate harbor return advised.
- Point to the mandatory safety disclaimer at the bottom:
  > *"Notice: Absence of observations is strictly evaluated as UNKNOWN/INSUFFICIENT EVIDENCE, never LOW or safe."*

### Spoken Explanation for Evaluators
> *"In Specialist 5, we test safety and vessel seaworthiness limits. 
> When we simulate a gale with 42-knot winds and 4.5-meter waves, the agent immediately escalates risk to CRITICAL with an emergency harbor return advisory. 
> Furthermore, if inland coordinates with missing marine data are queried, ORCA marks risk as UNKNOWN / INSUFFICIENT EVIDENCE. 
> Under maritime safety law, missing telemetry is NEVER evaluated as favorable or safe."*

---

## Minute 5: Ingestion Worker, Evidence Panel & View All 5 Mode

### Action
- At the top right of the dashboard, click the toggle: **View All 5 Agents**.
  - All 5 specialist cards (Weather, Ocean, Fishing Zone, Route, Safety/Risk) render concurrently on screen.
- In the right-hand panel, click the **Data Sources** tab under the Evidence Panel:
  - Review the active telemetry providers: Open-Meteo Weather, Open-Meteo Marine, NOAA ERDDAP (VIIRS Chlorophyll-a), and INCOIS PFZ bulletin worker.
- Explain the background **FisheriesIngestionWorker** lifecycle:
  - Runs asynchronously on backend startup without blocking requests.
  - Automatically isolates users from upstream NOAA ERDDAP outages using regionally bounded offline snapshots.

### Spoken Explanation for Evaluators
> *"Finally, we toggle 'View All 5 Agents' to demonstrate our decoupled parallel architecture. All five independent agents render concurrently. 
> In the Evidence Panel's 'Data Sources' tab, you see the active telemetry sources. 
> Our backend runs an asynchronous Fisheries Ingestion Worker via FastAPI lifespan. When NOAA ERDDAP experiences upstream 502 proxy errors, our client falls back to verified regional disk snapshots, stamping them with offline fixture indicators. 
> To conclude: ORCA has passed 201 backend unit tests, 17 live backend integration tests, 17 frontend service tests, and 20 headless Chrome browser checks—all with 100% pass rates."*

---

## Summary Checklist for Q&A

| Question From Evaluator | Verified System Answer |
| :--- | :--- |
| **How does ORCA handle missing fish data?** | It explicitly returns `status="insufficient_evidence"`, `suitability_score=null`, and `verified_fish_distribution="UNVERIFIED"`. Never fabricates data. |
| **Does favorable sea state grant sailing clearance?** | No. Physical wave feasibility is strictly decoupled from vessel navigation clearance and vessel seaworthiness. |
| **Are calculated routes certified passage plans?** | No. Routes are straight-line geodesic Great-Circle calculations and require authorized ENC/Admiralty charts. |
| **What happens if NOAA ERDDAP goes down?** | The client retries with backoff and serves a regionally bounded offline snapshot stamped with `cached_offline_snapshot`. |
