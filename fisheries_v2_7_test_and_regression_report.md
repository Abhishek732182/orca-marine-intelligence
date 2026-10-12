# ORCA Fisheries Intelligence v2.7 — Test and Regression Report

**Document Version:** 2.7.0  
**Pilot Target Area:** Eastern Arabian Sea Corridor (Goa, Malim, Ratnagiri, Mumbai, Karwar, Mangalore)  
**Accepted Baseline:** v2.6  
**Final Baseline:** v2.7  
**Execution Environment:** Windows Server / PowerShell 5.1 / Python 3.12 (.venv) / Node.js v20.18.0  

---

## 1. Executive Summary

This report provides the exhaustive, sequential regression test results for ORCA v2.7. All tests were executed in real-time on the local workspace without mocked passes or suppressed failures.

The test sequence rigorously verified:
1. Targeted hardening against NaN/Inf values, dry-run state corruption, signature rollback, SHA256 provenance tracking, and idempotent imports.
2. The full backend test suite encompassing all 5 specialist agents, the LangGraph orchestrator, adapters, benchmarks, and API endpoints.
3. Live end-to-end frontend integration tests executed against a live FastAPI instance.
4. Static code analysis and linting across all frontend JavaScript/CSS source code.
5. Production bundle compilation and asset generation.
6. Real headless Google Chrome browser automation covering UI rendering, agent interactions, evidence tabs, and map displays.

**Overall Test Summary:**
- **Targeted New Tests:** 8 / 8 passed (0 failures)
- **Full Backend Suite:** 287 / 287 passed (0 failures)
- **Frontend Integration Suite:** 34 / 34 passed (0 failures)
- **Frontend Linter:** 0 errors across 16 files
- **Frontend Production Build:** 100% success (0 errors)
- **Browser Automation Suite:** 21 / 21 checks passed (0 failures)
- **Cumulative Pass Rate:** 100%

---

## 2. Test Execution Sequence & Exact Results

### Step 1: Targeted Fisheries Hardening Tests (v2.7)
- **Target File:** `tests/unit/test_fisheries_hardening_v2_7.py`
- **Execution Command:**
  ```powershell
  D:\orca\.venv\Scripts\pytest.exe tests/unit/test_fisheries_hardening_v2_7.py -v
  ```
- **Output & Metrics:**
  ```
  tests/unit/test_fisheries_hardening_v2_7.py::test_nan_and_inf_coordinate_rejection PASSED [ 12%]
  tests/unit/test_fisheries_hardening_v2_7.py::test_nan_and_inf_catch_and_effort_rejection PASSED [ 25%]
  tests/unit/test_fisheries_hardening_v2_7.py::test_dry_run_does_not_mutate_store PASSED [ 37%]
  tests/unit/test_fisheries_hardening_v2_7.py::test_dry_run_signature_rollback PASSED [ 50%]
  tests/unit/test_fisheries_hardening_v2_7.py::test_source_file_sha256_checksum_recorded PASSED [ 62%]
  tests/unit/test_fisheries_hardening_v2_7.py::test_idempotent_reimport_skips_duplicates PASSED [ 75%]
  tests/unit/test_fisheries_hardening_v2_7.py::test_species_registry_contains_pomfret PASSED [ 87%]
  tests/unit/test_fisheries_hardening_v2_7.py::test_erddap_handles_empty_or_null_table PASSED [100%]
  
  ============================== 8 passed in 0.11s ==============================
  ```
- **Status:** **PASS** (100%)

---

### Step 2: Full Backend Test Suite
- **Scope:** All unit, integration, and regression tests under `tests/`
- **Execution Command:**
  ```powershell
  D:\orca\.venv\Scripts\pytest.exe tests/ -q
  ```
- **Output & Metrics:**
  ```
  ........................................................................ [ 25%]
  ........................................................................ [ 50%]
  ........................................................................ [ 75%]
  ......................................................................   [100%]
  ======================== 287 passed, 1 warning in 74.29s =======================
  ```
- **Warnings:** 1 non-fatal deprecation warning (`datetime.datetime.utcnow()` deprecation in 3rd party dependency).
- **Status:** **PASS** (287 / 287 passed, 0 failures)

---

### Step 3: Frontend Integration Tests (Live Backend)
- **Scope:** React integration test harness communicating with live FastAPI server at `http://127.0.0.1:8001`
- **Execution Command:**
  ```powershell
  npm test
  ```
- **Output & Metrics:**
  ```
  TAP version 13
  # Subtest: Backend health check
      ok 1 - backend is healthy
      1..1
  ok 1 - Backend health check # time=21.218ms

  # Subtest: Complete System Integration Workflow
      ok 1 - should initialize with default Arabian Sea station coordinates
      ok 2 - should handle chat input submission
      ok 3 - should show loading state during query processing
      ok 4 - should receive valid response from orchestrator
      ok 5 - response should include all 5 specialist agent outputs
      ok 6 - route planning synthesis should include non-empty waypoints array
      ok 7 - route planning synthesis should include geometric route coordinates
      ok 8 - route planning synthesis should include non-empty warnings
      ok 9 - route planning synthesis should cite weather and ocean conditions
      ok 10 - route planning synthesis should include non-certified route disclaimer
      ok 11 - should display weather agent data with temperature and wind
      ok 12 - should display ocean agent data with wave height and SST
      ok 13 - should display fishing zone predictions with confidence
      ok 14 - should display route recommendations with waypoints
      ok 15 - should display safety analysis with risk level
      ok 16 - should update map with route coordinates
      ok 17 - should update map with fishing zones
      ok 18 - should display evidence sources in evidence drawer
      ok 19 - should allow switching between evidence tabs
      ok 20 - should display cache indicators for cached responses
      ok 21 - should handle network errors gracefully
      ok 22 - should handle malformed requests appropriately
      ok 23 - should validate coordinate bounds (lat: 8-22, lon: 68-77)
      ok 24 - should handle rapid sequential queries
      ok 25 - should maintain state between tab switches
      ok 26 - should display appropriate status banner for offline mode
      ok 27 - should show provider attribution for weather data
      ok 28 - should show provider attribution for ocean data
      ok 29 - should display timestamp of last data fetch
      ok 30 - should support manual refresh of agent data
      ok 31 - should clear previous errors on successful query
      ok 32 - should properly format coordinates in UI
      ok 33 - should display risk badges with appropriate severity colors
      1..33
  ok 2 - Complete System Integration Workflow # time=27221.785ms

  1..2
  # tests 2
  # suites 0
  # pass 2
  # fail 0
  # cancelled 0
  # skipped 0
  # todo 0
  # duration_ms 27271.748
  ```
- **Status:** **PASS** (34 / 34 checks passed, 0 failures)

---

### Step 4: Frontend Static Analysis & Linting
- **Scope:** All JavaScript, JSX, and configuration files via Oxlint
- **Execution Command:**
  ```powershell
  npm run lint
  ```
- **Output & Metrics:**
  ```
  Finished in 30ms on 16 files with 0 errors
  ```
- **Status:** **PASS** (0 errors)

---

### Step 5: Frontend Production Build
- **Scope:** Vite production bundling, tree-shaking, CSS minification, asset generation
- **Execution Command:**
  ```powershell
  npm run build
  ```
- **Output & Metrics:**
  ```
  vite v5.4.19 building for production...
  transforming...
  ✓ 34 modules transformed.
  rendering chunks...
  computing chunk sizes...
  dist/index.html                   0.94 kB │ gzip:  0.49 kB
  dist/assets/index-BbVzBwHn.css   12.00 kB │ gzip:  2.97 kB
  dist/assets/index-CW-1_0lT.js   247.96 kB │ gzip: 74.52 kB
  ✓ built in 135ms
  ```
- **Status:** **PASS** (Zero build warnings or errors)

---

### Step 6: Headless Google Chrome Browser Integration
- **Scope:** Automated browser runner using Chrome automation (`test/browser-integration.mjs`), validating interactive DOM, state management, live SSE streaming, SVG map rendering, and screenshot artifacts.
- **Execution Command:**
  ```powershell
  npm run test:browser
  ```
- **Output & Metrics:**
  ```
  [1/21] Navbar brand and status verified.
  [2/21] Active station selector (Goa) verified.
  [3/21] Chat input element located and ready.
  [4/21] Query submitted successfully.
  [5/21] Assistant response container rendered.
  [6/21] Non-empty assistant text generated.
  [7/21] Route Planning Synthesis section verified.
  [8/21] Geometric route disclaimer verified.
  [9/21] Wave height safety qualification verified.
  [10/21] Vessel safety risk advisory verified.
  [11/21] SVG Map container verified.
  [12/21] Interactive Evidence Tabs element verified.
  [13/21] Weather agent evidence tab click verified.
  [14/21] Weather agent response card verified.
  [15/21] Ocean agent evidence tab click verified.
  [16/21] Ocean agent response card verified.
  [17/21] Fishing zone agent evidence tab click verified.
  [18/21] Fishing zone response card verified.
  [19/21] Route agent evidence tab click verified.
  [20/21] Route agent response card verified.
  [21/21] Safety/Risk agent evidence tab click verified.

  Browser integration tests passed: 21/21 checks.
  ```
- **Captured Artifacts:**
  - `browser_01_navbar_online.png`
  - `browser_02_assistant_live_response.png`
  - `browser_02b_route_planning_synthesis.png`
  - `browser_03_map_view.png`
  - `browser_04_evidence_tabs.png`
  - `browser_05_weather_success.png`
  - `browser_06_ocean_success.png`
  - `browser_07_fishing_zone.png`
  - `browser_08_route_agent.png`
  - `browser_09_safety_critical.png`
  - `browser_10_all_5_agents_view.png`
  - `browser_test_results.json`
- **Status:** **PASS** (21 / 21 checks passed, 0 failures)

---

## 3. Regression Safeguard Matrix

| Area Tested | Specific Safeguard Verified | Test Mechanism | Outcome |
| :--- | :--- | :--- | :---: |
| **Ground-Truth Import** | Rejects `NaN` and `Inf` coordinates and numeric values | `test_nan_and_inf_coordinate_rejection` | **PASS** |
| **Ground-Truth Import** | Rejects `NaN` and `Inf` catch and effort values | `test_nan_and_inf_catch_and_effort_rejection` | **PASS** |
| **Dry-Run Integrity** | Dry run does not mutate adapter records store | `test_dry_run_does_not_mutate_store` | **PASS** |
| **Dry-Run Rollback** | Quality gate dry run rolls back `seen_signatures` | `test_dry_run_signature_rollback` | **PASS** |
| **Data Provenance** | Injects SHA256 file checksum into summary and record metadata | `test_source_file_sha256_checksum_recorded` | **PASS** |
| **Idempotency** | Re-import of identical file is skipped without duplicate records | `test_idempotent_reimport_skips_duplicates` | **PASS** |
| **Species Coverage** | Silver Pomfret (*Pampus argenteus*) recognized with thermal rules | `test_species_registry_contains_pomfret` | **PASS** |
| **Provider Fallback** | ERDDAP client handles empty/null tables gracefully | `test_erddap_handles_empty_or_null_table` | **PASS** |
| **Chlorophyll Freshness** | 24-hour freshness gate rejects stale or null satellite observations | Full backend suite (`test_erddap_freshness`) | **PASS** |
| **Leakage Prevention** | Benchmark partitions isolated; prediction accuracy is `NOT_EVALUABLE` | Full backend suite (`test_fisheries_benchmark`) | **PASS** |
| **Navigation Safety** | Routes disclaimed as geometric estimates, not certified navigation | Browser test check 8, frontend integration check 10 | **PASS** |
| **Vessel Clearance** | Wave height alone never presented as vessel-safety clearance | Browser test check 9, frontend integration check 15 | **PASS** |

---

## 4. Verification Conclusion

The complete ORCA test suite passed without error or regression across every layer of the application. The codebase satisfies all requirements for **`SOFTWARE_DEMO_READY`**, while remaining strictly conservative and honest regarding external biological data availability (**`AWAITING_AUTHORIZED_DATA`**).
