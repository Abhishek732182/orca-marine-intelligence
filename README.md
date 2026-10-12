# ORCA — Marine Intelligence & Fishing Advisory Platform

[![Backend Tests](https://img.shields.io/badge/Backend%20Tests-201%20Passing-brightgreen)](file:///d:/orca)
[![Live Integration](https://img.shields.io/badge/Live%20Integration-17%20Passing-brightgreen)](file:///d:/orca)
[![Frontend Services](https://img.shields.io/badge/Frontend%20Services-17%20Passing-brightgreen)](file:///d:/orca)
[![Headless Chrome E2E](https://img.shields.io/badge/Headless%20Chrome-20%2F20%20Passing-brightgreen)](file:///d:/orca)
[![Python](https://img.shields.io/badge/Python-3.13-blue)](file:///d:/orca)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-teal)](file:///d:/orca)
[![LangGraph](https://img.shields.io/badge/LangGraph-Stateful%20Workflows-orange)](file:///d:/orca)
[![React](https://img.shields.io/badge/React-19.2-cyan)](file:///d:/orca)

ORCA is an evidence-grounded marine intelligence and voyage advisory platform engineered for artisanal fishers, vessel masters, and maritime authorities. Built with Python, FastAPI, LangGraph, and React 19, ORCA integrates real-time atmospheric, oceanographic, and satellite remote sensing telemetry through five decoupled specialist agents, a master mission orchestrator, an autonomous workspace assistant, and a resilient background fisheries ingestion worker.

---

## Table of Contents
1. [Core Principles & Safety Guarantees](#core-principles--safety-guarantees)
2. [System Architecture](#system-architecture)
3. [Agent Ecosystem & Specialist Agents](#agent-ecosystem--specialist-agents)
4. [Data Ingestion & Resilient Offline Modes](#data-ingestion--resilient-offline-modes)
5. [Prerequisites & Environment Setup](#prerequisites--environment-setup)
6. [Running the Application](#running-the-application)
7. [Running the Test Suites](#running-the-test-suites)
8. [API Endpoints Reference](#api-endpoints-reference)
9. [Five-Minute Demonstration Script](#five-minute-demonstration-script)
10. [Troubleshooting & FAQ](#troubleshooting--faq)
11. [Limitations & Future Roadmap](#limitations--future-roadmap)

---

## Core Principles & Safety Guarantees

ORCA is designed around strict operational safety and scientific evidence grounding:

1. **Zero Data Fabrication**: Never simulates or invents unverified fish coordinates, biomass concentrations, catch probabilities, or satellite values.
2. **Strict `INSUFFICIENT_EVIDENCE` Preservation**: If biological fish distributions or satellite ocean-color feeds are missing or unverified, the system explicitly marks status as `insufficient_evidence` with null numeric scores.
3. **Decoupled Craft Operability vs. Maritime Safety Clearance**: Favorable wave height evaluates vessel craft limits only; it does **not** grant maritime sailing clearance or guarantee fish availability.
4. **Non-Navigable Geodesic Route Estimates**: Geodesic Great-Circle distance calculations are straight-line estimates and **not** certified navigable passages. Bathymetry, shoals, underwater obstructions, landmass avoidance, and Traffic Separation Schemes (TSS) are unverified; mariners must consult authorized hydrographic charts (ENC/Admiralty).
5. **Decoupled Architecture**: All five specialist agents operate independently and can be invoked in isolation without dependency on a central orchestrator.

---

## System Architecture

### Architectural Overview Diagram

```
+---------------------------------------------------------------------------------------+
|                                    REACT FRONTEND                                     |
|  - AI Workspace Assistant (Chat Composer, Execution Plan, Approval Gates, Live Log)  |
|  - Maritime Leaflet/SVG Map (Depth Contours, 442km Route, Port Nodes, Layers)         |
|  - Evidence Panel Tabs (Data Sources, Live Forecast Charts, Parameter Breakdown)     |
|  - Specialist Agent Panels (Weather, Ocean, Fishing Zone, Route, Safety/Risk)        |
+------------------------------------------+--------------------------------------------+
                                           | HTTP REST / JSON
                                           v
+---------------------------------------------------------------------------------------+
|                               FASTAPI APPLICATION (PORT 8010)                         |
|  Lifespan Context Manager: Controls Non-Blocking FisheriesIngestionWorker             |
+------------------------------------------+--------------------------------------------+
       |                                   |                                   |
       v                                   v                                   v
+------------------+             +--------------------+              +------------------+
| AI WORKSPACE     |             | MASTER MISSION     |              | FIVE INDEPENDENT |
| ASSISTANT        |             | ORCHESTRATOR       |              | SPECIALISTS      |
| (Agent 6 Chat)   |             | (LangGraph Graph)  |              | (Direct Routes)  |
| - Intent Parser  |             | - Step 1: Plan     |              | 1. Weather       |
| - Execution Plan |             | - Step 2: Parallel |              | 2. Ocean         |
| - Approval Gate  |             | - Step 3: Synthesis|              | 3. Fishing Zone  |
| - Tool Dispatch  |             |                    |              | 4. Route         |
+--------+---------+             +---------+----------+              | 5. Safety/Risk   |
         |                                 |                         +--------+---------+
         +---------------------------------+----------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                                  DATA PROVIDER LAYER                                  |
|  - Open-Meteo Weather API (Live atmospheric data: wind, temp, Beaufort scale)        |
|  - Open-Meteo Marine API (Live oceanographic wave heights, swell, sea-state code)    |
|  - FisheriesIngestionWorker (Asynchronous background polling worker)                 |
|      * INCOIS PFZ Client (GeoJSON bulletin parsing, ray-casting point-in-polygon)    |
|      * NOAA ERDDAP Client (VIIRS Chlorophyll-a / SST, regional cache bounding box)    |
+---------------------------------------------------------------------------------------+
```

### Data-Flow Lifecycle

1. **User Request**: User issues a natural-language mission goal in the workspace assistant or selects a specialist agent form.
2. **Planning & Tool Dispatch**: The Orchestrator or Assistant validates coordinates and determines necessary specialist queries.
3. **Parallel Specialist Execution**: Specialist agents execute concurrently (`asyncio.gather`), querying live upstream APIs or local snapshot caches.
4. **Validation & Quality Control**: Measurements are validated against physical plausibility bounds (e.g. wave height 0–30m, SST -2–45°C), WMO Code 3700 Douglas Sea Scale tables, and documented freshness policies.
5. **Synthesis & Advisory**: Orchestrator reconciles observations, checks for discrepancies, escalates severe hazards to `CRITICAL`, preserves `INSUFFICIENT_EVIDENCE` for unobserved variables, and returns a verified JSON payload.

---

## Agent Ecosystem & Specialist Agents

| Agent | Module | Primary Function | Data Sources |
| :--- | :--- | :--- | :--- |
| **1. Weather Agent** | [weather_agent.py](file:///d:/orca/backend/app/agents/weather_agent.py) | Atmospheric telemetry: air temp, wind speed/direction, Beaufort scale, precipitation. | Open-Meteo Weather API |
| **2. Ocean Agent** | [ocean_agent.py](file:///d:/orca/backend/app/agents/ocean_agent.py) | Sea state classification: significant wave height ($H_s$), swell waves, WMO Code 3700. | Open-Meteo Marine API |
| **3. Fishing Zone Agent** | [fishing_zone_agent.py](file:///d:/orca/backend/app/agents/fishing_zone_agent.py) | Vessel craft operability vs biological fisheries habitat suitability; species thermal matching. | Open-Meteo Marine, INCOIS PFZ, NOAA ERDDAP |
| **4. Route Agent** | [route_agent.py](file:///d:/orca/backend/app/agents/route_agent.py) | Geodesic Great-Circle distances, waypoint bearings, estimated transit time. | Geodesic Haversine Math |
| **5. Safety/Risk Agent** | [safety_risk_agent.py](file:///d:/orca/backend/app/agents/safety_risk_agent.py) | Multi-factor risk scoring (LOW, MEDIUM, HIGH, CRITICAL); severe gale emergency escalation. | Multi-agent telemetry synthesis |
| **6. Orchestrator Agent** | [orchestrator_agent.py](file:///d:/orca/backend/app/agents/orchestrator_agent.py) | Master mission orchestrator using LangGraph stateful DAG for parallel specialist dispatch. | Specialist Agents 1–5 |
| **AI Workspace Assistant** | [assistant_agent.py](file:///d:/orca/backend/app/agents/assistant_agent.py) | Natural language interface, multi-step execution plans, human approval gates, and tool dispatch. | Specialist Tool Registry |

---

## Data Ingestion & Resilient Offline Modes

ORCA integrates a resilient fisheries data ingestion worker supporting three operating modes:

```
[Upstream Query: NOAA ERDDAP / INCOIS]
                 |
        +--------+--------+
        |                 |
  (HTTP 200 OK)     (502/Timeout)
        |                 |
        v                 v
[Validate Data]    [Check Regional Cache]
        |                 |
        v                 v
[Persist Snapshot] [Bounding Box Match?]
        |            /          \
        |         (Yes)         (No)
        |           |             |
        v           v             v
   [LIVE MODE] [OFFLINE CACHED] [INSUFFICIENT EVIDENCE]
```

1. **`live` Mode**: Direct real-time HTTPS queries to official endpoints. Successfully validated responses are saved as snapshots.
2. **`offline_cached` Mode**: If NOAA ERDDAP returns an upstream HTTP 502/503/504 error or times out, the client falls back to disk snapshots matching the requested geographic bounding box `[min_lat, max_lat, min_lon, max_lon]`.
3. **`fixture` Mode**: Air-gapped testing mode reading verified GeoJSON and ERDDAP table JSON files from `tests/fixtures/`.
4. **Staleness Tracking**: Cached records retain original observation timestamps and snapshot age. Snapshots older than 24 hours are stamped with `status="stale"`.
5. **Cross-Region Misses**: If requested coordinates fall outside cached snapshot boundaries, the client returns an explicit empty list, preventing false spatial attribution.

---

## Prerequisites & Environment Setup

### Prerequisites
- **Python**: 3.11, 3.12, or 3.13
- **Node.js**: v18.0.0 or higher (v20+ recommended)
- **PowerShell** (Windows) or **Bash** (macOS/Linux)
- **Google Chrome** (for running headless browser verification suite)

### Environment Configuration

Create a `.env` file in the project root:

```bash
# Core API Settings
APP_NAME=ORCA Marine Intelligence API
APP_VERSION=0.1.0
ENVIRONMENT=development

# Optional Frontend Origin
FRONTEND_ORIGIN=http://127.0.0.1:5173

# Fisheries & Satellite Data Ingestion Configuration
# Institutional INCOIS credentials (optional)
INCOIS_PFZ_URL=
INCOIS_API_KEY=

# Copernicus Marine Service credentials (optional)
COPERNICUS_MARINE_USERNAME=
COPERNICUS_MARINE_PASSWORD=

# NOAA ERDDAP Configuration
ERDDAP_BASE_URL=https://coastwatch.pfeg.noaa.gov/erddap
ERDDAP_MODE=live_with_fallback   # live_with_fallback | fixture_only | live_only

# Background Worker & Cache
FISHERIES_CACHE_DIR=data/fisheries_cache
FISHERIES_INGESTION_ENABLED=true
FISHERIES_INGESTION_INTERVAL_SECONDS=3600
```

Frontend environment configuration (`frontend/.env`):
```bash
VITE_ORCA_API_URL=http://127.0.0.1:8010
```

---

## Running the Application

### 1. Start the FastAPI Backend (Port 8010)
```powershell
# In project root:
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = "d:\orca\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```
- Interactive Swagger Documentation: `http://127.0.0.1:8010/docs`
- Health Endpoint: `http://127.0.0.1:8010/api/health`

### 2. Start the React Frontend (Port 5173)
```powershell
cd d:\orca\frontend
npm run dev
```
- Frontend Dashboard: `http://127.0.0.1:5173/`

---

## Running the Test Suites

All tests are reproducible and verified:

```powershell
# 1. Complete Backend Regression Suite (201 tests)
cd d:\orca
.\.venv\Scripts\pytest.exe

# 2. Live API Integration & Frontend Unit Suite (34 tests)
cd d:\orca\frontend
$env:VITE_ORCA_API_URL = "http://127.0.0.1:8010"
npm test

# 3. Headless Chrome Browser CDP Suite (20 checks)
cd d:\orca\frontend
npm run test:browser
```

### Verified Test Summary

```
======================================================================
TOTAL VERIFIED AUTOMATED TEST RESULTS:
----------------------------------------------------------------------
Backend Unit & Ingestion Tests:      201 / 201 PASSED (56.40s)
Live Backend Integration Tests:       17 /  17 PASSED (25.82s)
Frontend Service Unit Tests:          17 /  17 PASSED (10.74ms)
Headless Google Chrome CDP Checks:    20 /  20 PASSED (42.10s)
----------------------------------------------------------------------
COMBINED TEST COVERAGE:              255 / 255 PASSED (100% SUCCESS)
======================================================================
```

---

## API Endpoints Reference

### Core Endpoints
- `GET /api/health` — Service health check and phase indicator.
- `GET /api/marine/wave-height?latitude=15.0&longitude=72.0` — Direct marine wave observations.

### Specialist Agent Endpoints
- `POST /api/agents/weather/analyze` — Query Weather Agent for atmospheric observations.
- `POST /api/agents/ocean/analyze` — Query Ocean Agent for wave heights and WMO sea-state classification.
- `POST /api/agents/fishing-zone/analyze` — Query Fishing Zone Agent for vessel operability and fisheries indicators.
- `POST /api/agents/route/analyze` — Query Route Agent for geodesic straight-line distance and passage legs.
- `POST /api/agents/safety-risk/analyze` — Query Safety/Risk Agent for multi-factor safety evaluation.

### Orchestrator & Assistant Endpoints
- `POST /api/agents/orchestrator/analyze` — Concurrently invoke all five specialists and synthesize mission advisory.
- `POST /api/agents/assistant/chat` — Conversational natural-language planning and specialist tool dispatch.
- `GET /api/agents/assistant/tools` — List registered specialist tools.
- `POST /api/agents/assistant/approve` — Approve or reject human-in-the-loop tool execution steps.

---

## Five-Minute Demonstration Script

For a detailed, minute-by-minute walkthrough with teacher explanations, see [docs/DEMONSTRATION_SCRIPT.md](file:///d:/orca/docs/DEMONSTRATION_SCRIPT.md).

1. **Minute 1: Overview & Navbar Health**
   - Open `http://127.0.0.1:5173/`.
   - Point out the light-theme canvas, responsive sidebar, and green **API: ONLINE** status badge.
2. **Minute 2: AI Workspace Assistant (Agent 6)**
   - Send: `"Plan passage from Goa (15.0, 72.0) to Mumbai (18.9, 72.8)"`.
   - Review 3-step execution plan, live Route Agent dispatch, Great-Circle distance (442 km), and amber **Nautical Navigation Disclaimer**.
3. **Minute 3: Specialist 3 (Fishing Zone Agent)**
   - Navigate to **Specialist Agents -> Fishing Zone Agent**.
   - Query Goa coordinates (`15.0`, `72.0`) for *Mackerel*.
   - Review the `LIVE OBSERVATIONS` badge, physical wave operability (`FAVORABLE`), and unobserved fish distribution (`UNVERIFIED` / `INSUFFICIENT_EVIDENCE`). Explain why wave physics alone does not prove fish presence.
4. **Minute 4: Specialist 5 (Safety/Risk Agent)**
   - Select **Safety/Risk Agent**.
   - Click **Simulate Severe Gale (42 kts, 4.5m waves)**.
   - Observe immediate risk escalation to **CRITICAL RISK** with red danger alert banner. Explain the safety principle: *absence of telemetry is never evaluated as safe*.
5. **Minute 5: Ingestion Worker & View All 5 Mode**
   - Toggle **View All 5 Agents** at the top right to display all five panels concurrently.
   - Switch to the **Data Sources** tab in the evidence panel to review provider operating modes (Open-Meteo live, ERDDAP resilient cache, INCOIS GeoJSON bulletins).

---

## Troubleshooting & FAQ

#### 1. Why do tests report `ECONNREFUSED 127.0.0.1:8001`?
By default, the client library defaults to port 8001 if no environment variable is provided. Set `$env:VITE_ORCA_API_URL = "http://127.0.0.1:8010"` prior to running tests.

#### 2. Why does the Fishing Zone Agent return `INSUFFICIENT_EVIDENCE`?
This is an intentional scientific guarantee. Open-Meteo supplies wave physics only. Without direct acoustic sonar fish surveys, commercial catch landings, or validated satellite chlorophyll composites, ORCA strictly refuses to fabricate fish presence.

#### 3. Why is the route marked as a straight-line estimate?
Geodesic distance calculations use the Great-Circle Haversine formula. They do not account for underwater shoals, bathymetry, islands, or shipping channels. Mariners must consult authorized nautical charts before passage.

---

## Limitations & Future Roadmap

1. **Institutional INCOIS API Access**: Official INCOIS Potential Fishing Zone REST feeds require government institutional clearance. When unauthenticated, ORCA operates in local GeoJSON bulletin mode.
2. **NOAA ERDDAP Availability**: Real NOAA ERDDAP servers experience periodic upstream HTTP 502 Proxy Errors. ORCA's regional snapshot caching isolates users from these outages.
3. **Commercial Biomass Telemetry**: Direct pelagic fish biomass requires acoustic sonar surveys or catch logbooks. Future integrations will support echosounder data formats (EK60/EK80).
