# ORCA Fisheries Intelligence v2.3 — Data Readiness & Independent Reproducibility Report

**Milestone:** v2.3 Phase 1: Independent Reproducibility and Fisheries Data Readiness  
**Project Root:** `D:\orca`  
**Manifest Reference:** `data/benchmarks/reproducibility_manifest.json`  
**Reference Clock (UTC):** `2026-10-12T04:00:00Z`  
**Evaluator Engine:** [backend/app/evaluation/fisheries_benchmark.py](file:///d:/orca/backend/app/evaluation/fisheries_benchmark.py)

---

## 1. Executive Summary & Root-Cause Investigation

### A. The Reported 100% Chlorophyll Coverage Investigation
In the initial v2.2 benchmark, chlorophyll-a coverage was reported as 100% (5/5 stations). A rigorous Phase 1 audit of the underlying live NOAA ERDDAP CoastWatch VIIRS service (`noaacwNPPVIIRSSQchlaDaily`) across all five target stations in the Arabian Sea revealed:
1. **HTTP 200 Response:** NOAA CoastWatch successfully answered all requests with HTTP status 200 and returned valid tabular JSON containing between 9 and 16 spatial grid cells per bounding box.
2. **100% Cloud-Masked Null Values:** In every single returned grid cell across all five stations, `raw_value = None`. Seasonal post-monsoon cloud cover completely masked satellite optical sensor detection of surface chlorophyll-a.
3. **Observation Age Exceeded (Stale Pass):** The latest satellite observation timestamp across the entire region was `2026-10-02T12:00:00Z`. At the benchmark evaluation time (`2026-10-12T04:00:00Z`), this pass is **240 hours (10 days) old**, drastically exceeding the configured 24-hour satellite ocean-color freshness policy.
4. **Root Cause & Correction:** The previous 100% metric was measured against a synthetic partition with non-null placeholder floats. When evaluated against actual live satellite retrieval, **usable, fresh chlorophyll coverage is 0.0% (0/5)**. Inferring usable coverage from HTTP 200 status or grid-cell counts alone was a false positive.

### B. Summary of Genuine Operational Data Readiness
- **Wave & Sea State:** **100.0% (5/5)** live validated coverage via Open-Meteo Marine wave forecasts.
- **Sea Surface Temperature (SST):** **100.0% (5/5)** live validated coverage via Open-Meteo Marine numerical SST ($29.1^\circ\text{C} - 30.8^\circ\text{C}$).
- **Usable Fresh Chlorophyll-a:** **0.0% (0/5)** due to $100\%$ cloud masking and 10-day-old satellite telemetry.
- **Ground-Truth Biological Catch / Survey Telemetry:** **0.0% (0/5)** unintegrated in the repository.

---

## 2. Station-by-Station Reproducibility Manifest

Live provider audit results recorded in `data/benchmarks/reproducibility_manifest.json`:

| Station ID | Station Name | Requested Coords | Source / Dataset ID | Variable | Raw Value | Obs Timestamp | Freshness Age & Policy | Provenance Category | Baseline Eligible? |
|---|---|---|---|---|---|---|---|---|---|
| **`IND-GOA-01`** | Goa Offshore | 15.0°N, 72.0°E | `open-meteo-marine` | `wave_height` | `0.9 m` | `2026-10-12T00:00Z` | 4.0h ($\le$ forecast) | `LIVE_VALIDATED` | **Yes** |
| | | | `open-meteo-marine` | `sea_surface_temperature` | `30.8 °C` | `2026-10-12T00:00Z` | 4.0h ($\le$ 6.0h SST) | `LIVE_VALIDATED` | **Yes** |
| | | | `noaacwNPPVIIRSSQchlaDaily` | `chlorophyll_a` | `None` (Cloud) | `2026-10-02T12:00Z` | 240h ($> 24$h limit) | `STALE_OBSERVATION` | **No** |
| | | | *Unintegrated* | `fish_biomass` | `None` | `None` | Missing | `UNAVAILABLE_PROVIDER` | **No** |
| **`IND-BOM-01`** | Mumbai Shelf | 18.9°N, 72.5°E | `open-meteo-marine` | `wave_height` | `0.82 m` | `2026-10-12T00:00Z` | 4.0h ($\le$ forecast) | `LIVE_VALIDATED` | **Yes** |
| | | | `open-meteo-marine` | `sea_surface_temperature` | `30.0 °C` | `2026-10-12T00:00Z` | 4.0h ($\le$ 6.0h SST) | `LIVE_VALIDATED` | **Yes** |
| | | | `noaacwNPPVIIRSSQchlaDaily` | `chlorophyll_a` | `None` (Cloud) | `2026-10-02T12:00Z` | 240h ($> 24$h limit) | `STALE_OBSERVATION` | **No** |
| | | | *Unintegrated* | `fish_biomass` | `None` | `None` | Missing | `UNAVAILABLE_PROVIDER` | **No** |
| **`IND-KRW-01`** | Karwar Coastal | 14.8°N, 73.5°E | `open-meteo-marine` | `wave_height` | `0.68 m` | `2026-10-12T00:00Z` | 4.0h ($\le$ forecast) | `LIVE_VALIDATED` | **Yes** |
| | | | `open-meteo-marine` | `sea_surface_temperature` | `30.8 °C` | `2026-10-12T00:00Z` | 4.0h ($\le$ 6.0h SST) | `LIVE_VALIDATED` | **Yes** |
| | | | `noaacwNPPVIIRSSQchlaDaily` | `chlorophyll_a` | `None` (Cloud) | `2026-10-02T12:00Z` | 240h ($> 24$h limit) | `STALE_OBSERVATION` | **No** |
| | | | *Unintegrated* | `fish_biomass` | `None` | `None` | Missing | `UNAVAILABLE_PROVIDER` | **No** |
| **`IND-MNG-01`** | Mangalore Shelf | 12.8°N, 74.0°E | `open-meteo-marine` | `wave_height` | `0.9 m` | `2026-10-12T00:00Z` | 4.0h ($\le$ forecast) | `LIVE_VALIDATED` | **Yes** |
| | | | `open-meteo-marine` | `sea_surface_temperature` | `30.8 °C` | `2026-10-12T00:00Z` | 4.0h ($\le$ 6.0h SST) | `LIVE_VALIDATED` | **Yes** |
| | | | `noaacwNPPVIIRSSQchlaDaily` | `chlorophyll_a` | `None` (Cloud) | `2026-10-02T12:00Z` | 240h ($> 24$h limit) | `STALE_OBSERVATION` | **No** |
| | | | *Unintegrated* | `fish_biomass` | `None` | `None` | Missing | `UNAVAILABLE_PROVIDER` | **No** |
| **`IND-VRL-01`** | Veraval Coast | 20.8°N, 69.8°E | `open-meteo-marine` | `wave_height` | `0.9 m` | `2026-10-12T00:00Z` | 4.0h ($\le$ forecast) | `LIVE_VALIDATED` | **Yes** |
| | | | `open-meteo-marine` | `sea_surface_temperature` | `29.1 °C` | `2026-10-12T00:00Z` | 4.0h ($\le$ 6.0h SST) | `LIVE_VALIDATED` | **Yes** |
| | | | `noaacwNPPVIIRSSQchlaDaily` | `chlorophyll_a` | `None` (Cloud) | `2026-10-02T12:00Z` | 240h ($> 24$h limit) | `STALE_OBSERVATION` | **No** |
| | | | *Unintegrated* | `fish_biomass` | `None` | `None` | Missing | `UNAVAILABLE_PROVIDER` | **No** |

---

## 3. Provenance Category Distribution

Across all 20 evaluated station-variable observation vectors:
- **`LIVE_VALIDATED`:** 10 records (5 wave height + 5 sea surface temperature) $\rightarrow$ **100% eligible for active baseline**.
- **`STALE_OBSERVATION`:** 5 records (5 satellite chlorophyll-a passes exceeding 24h) $\rightarrow$ **Excluded from active baseline**.
- **`UNAVAILABLE_PROVIDER`:** 5 records (5 biological biomass queries) $\rightarrow$ **Excluded from active baseline**.
- **`CACHED_OBSERVATION`:** 0 records (no local cache stored).
- **`OFFLINE_FIXTURE`:** 0 records in manifest (retained strictly within fixture partition).

---

## 4. Genuine Fisheries Catch & Survey Records Research

A thorough audit confirms **no genuine commercial fisheries catch registers or in-situ survey records currently exist** in the repository.

### Realistic Official Data-Access Options & Permission Roadmap:
1. **CMFRI (Central Marine Fisheries Research Institute, ICAR, India):**
   - **Repository:** National Marine Fisheries Data Repository / Fish Catch Survey Coordination (FCSC).
   - **Data Structure:** Multi-stage stratified random sampling of commercial fish landings across 1,511 landing centers in India. Includes species, gear, effort, catch weight (kg), and zonal coordinates.
   - **Access / Permissions:** Formal institutional MOU or application to Director, ICAR-CMFRI (Kochi); requires non-disclosure agreement (NDA) and ICAR KRISHI portal credentials.
2. **INCOIS PFZ Live Web Feature Service (MoES, India):**
   - **Repository:** INCOIS Marine Fishery Advisory System.
   - **Data Structure:** GeoJSON/Shapefile polygons of thermal/chlorophyll frontal convergences with advised landing centers and bearing.
   - **Access / Permissions:** Formal institutional registration at `incois.gov.in`; issuance of production API key (`API_KEY_ORCA_INCOIS_PROD`) and IP whitelisting.
3. **OBIS (Ocean Biodiversity Information System, UNESCO-IOC):**
   - **Repository:** OBIS REST API (`api.obis.org`) / GBIF Marine Occurrences.
   - **Data Structure:** Georeferenced species presence records (Darwin Core Archive). Open access (CC-BY).
   - **Limitations:** Provides historical species occurrence points, but does not provide real-time catch abundance or biomass density.
4. **NOAA NMFS (National Marine Fisheries Service, USA):**
   - **Repository:** Fisheries One Stop Shop (FOSS) Commercial Landings Database / InPort Telemetry.
   - **Data Structure:** Public open government acoustic and trawl survey data for US Exclusive Economic Zone (EEZ). Open access, but geographically outside the Indian Ocean.

---

## 5. Regression Test Results

### Test Execution Metrics
| Suite | Target | Executed Tests | Result | Duration |
|---|---|---|---|---|
| **v2.3 Data Readiness Suite** | `pytest tests/unit/test_fisheries_v2_3_readiness.py` | 8 | **8 passed** | 0.05s |
| **v2.2 Benchmark Suite** | `pytest tests/unit/test_fisheries_benchmark_v2_2.py` | 10 | **10 passed** | 0.04s |
| **All Backend Unit Tests** | `pytest tests/unit -q` | 244 | **244 passed** | 1m 12s |
| **Backend Integration Tests** | `pytest tests/test_e2e_integration.py tests/test_health.py` | 9 | **9 passed** | 0.65s |
| **Total Backend Test Suite** | `pytest tests/` | 253 | **253 passed** | 1m 15s |
| **Frontend Test Suite** | `cd frontend && npm test` | 34 | **34 passed** | 25.6s |
| **Live Browser Test Suite** | `node frontend/scripts/run-browser-tests.js` | 21 | **21/21 passed** | 42.1s |

### Exact Changed & Created Files
- **Created:**
  - `data/benchmarks/reproducibility_manifest.json` (Full station reproducibility catalog)
  - `backend/tests/unit/test_fisheries_v2_3_readiness.py` (v2.3 deterministic regression suite)
  - `tests/unit/test_fisheries_v2_3_readiness.py` (Root mirror for pytest discovery)
  - `fisheries_v2_3_data_readiness_report.md` (This data readiness audit)
- **Modified:**
  - `backend/app/evaluation/fisheries_benchmark.py`: Hardened `evaluate_chlorophyll_coverage` with cloud-mask filtering, spatial tolerance verification, and manifest evaluation methods (`evaluate_reproducibility_manifest` and `load_reproducibility_manifest`).
- **Preserved:**
  - All existing v2.1 and v2.2 APIs, schemas, LangGraph workflows, and UI component behavior.
