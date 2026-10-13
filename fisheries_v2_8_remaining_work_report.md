# ORCA Fisheries Intelligence v2.8 — Remaining Work Completion & Issue Inventory Report

**Document Version:** 2.8.0  
**Pilot Target Area:** Eastern Arabian Sea Corridor (Goa, Malim, Ratnagiri, Mumbai, Karwar, Mangalore)  
**Accepted Baseline:** v2.7  
**Final Baseline:** v2.8  
**Operational Biological Store Status:** `AWAITING_AUTHORIZED_DATA`  

---

## 1. Executive Summary

ORCA v2.8 delivers the complete engineering hardening, safe real-data onboarding pipeline, benchmark integrity guards, and comprehensive verification suite for the ORCA Marine Intelligence Platform.

Key accomplishments of this milestone:
1. **Repository Audit & Baseline Verification:** Independently verified all backend data-source adapters, specialist agents, LangGraph orchestrator, benchmark partition validator, and React frontend.
2. **Issue Inventory & Defect Remediation:** Classified all findings into the required categories (`BUG`, `SECURITY_RISK`, `DATA_QUALITY_RISK`, `MISSING_FEATURE`, `EXTERNAL_DEPENDENCY`, `OPTIONAL_IMPROVEMENT`) and resolved confirmed internal defects with surgical, non-breaking modifications.
3. **Data Invariance & Zero Fabrication:** Preserved the operational biological store as `AWAITING_AUTHORIZED_DATA` (0 records). No synthetic fish catches, speculative CPUE values, or unverified occurrences were fabricated.
4. **Benchmark & Leakage Hardening:** Eliminated dummy prediction accuracy metrics; predictive classification strictly computes real confusion matrix metrics when predictions are provided and returns `NOT_EVALUABLE` when predictions are absent.
5. **CMFRI Requisition Workflow Completion:** Formalized the official data requisition package for ICAR-CMFRI, Kochi, covering 2023–2025 landing statistics for Malim, Mirkarwada, Sasoon Docks, Karwar, and Mangalore.
6. **Exhaustive Multi-Tier Regression:** Validated the application through 6 sequential testing layers (targeted tests, full backend suite, frontend integration tests against active backend, linter, production build, and headless Google Chrome browser automation).

---

## 2. Issue Inventory & Classification

| Finding ID | Classification | Component / File | Evidence & Root Cause | Implemented Resolution | Verification Status |
| :---: | :---: | :--- | :--- | :--- | :---: |
| **ORCA-V28-01** | **DATA_QUALITY_RISK** / **BUG** | `backend/app/data_sources/biological_adapter.py` | In `normalize_record()`, records with `ev_rec.status == "invalid"` (e.g. `is_authorized_official_feed=False`) were committed to `self._normalized_records` if `commit=True`, contaminating operational storage with quarantined data. | Gated operational store commits on `if commit and ev_rec.status == "valid":`. Added explicit `r.status == "valid"` filter to `fetch()`. | **PASSED** (Store count verified 0 when unauthorized records processed) |
| **ORCA-V28-02** | **DATA_QUALITY_RISK** / **BUG** | `backend/app/evaluation/fisheries_benchmark.py` | In `evaluate_classification_accuracy()`, if labeled records were passed, the engine returned hardcoded placeholder `value=1.0` without evaluating model predictions against true labels. | Replaced dummy `1.0` with true confusion matrix computation (TP, FP, TN, FN, Accuracy, Precision, Recall, F1) if predictions exist, or `not_evaluable` if predictions are absent. | **PASSED** (Verified in unit tests) |
| **ORCA-V28-03** | **DATA_QUALITY_RISK** / **BUG** | `backend/app/data_sources/ground_truth_import.py` | CSV files exported from Windows Excel or Indian institutional portals containing a UTF-8 Byte Order Mark (`\ufeff`) caused the first header (e.g. `\ufeffrecord_identifier`) to fail alias mapping. | Added `.lstrip("\ufeff")` during CSV header normalization in `_resolve_header_mapping()`. | **PASSED** (BOM headers resolved to canonical columns) |
| **ORCA-V28-04** | **DATA_QUALITY_RISK** | `backend/app/data_sources/ground_truth_import.py` | `import_csv()` lacked upfront syntax rejection for negative `spatial_uncertainty_km`, negative `catch_weight`, and non-positive `effort_hours`. | Added explicit validation and machine-readable rejection codes (`negative_spatial_uncertainty`, `negative_catch_weight`, `non_positive_effort_hours`). | **PASSED** (Rejected with explicit reason codes) |
| **ORCA-V28-05** | **EXTERNAL_DEPENDENCY** | Ground-Truth Landings Data | ICAR-CMFRI 2023–2025 commercial landing statistics for the 5 pilot landing centers require official institutional data delivery. | Operational biological store maintained at 0 records (`AWAITING_AUTHORIZED_DATA`). Complete requisition package prepared for CMFRI Director. | **MONITORED** (No synthetic records fabricated) |
| **ORCA-V28-06** | **EXTERNAL_DEPENDENCY** | Satellite Chlorophyll Telemetry | NOAA CoastWatch VIIRS high cloud masking produces 100% null/masked cells over the Eastern Arabian Sea corridor; passes $>10$ days old. | Enforced strict 24-hour freshness policy. Live Arabian Sea chlorophyll coverage transparently reported as `0.0%` with clear UI banner. | **VERIFIED** (24h freshness gate active) |
| **ORCA-V28-07** | **EXTERNAL_DEPENDENCY** | INCOIS PFZ Production API | Automated programmatic polling of official INCOIS Potential Fishing Zone bulletins requires institutional API credentials (`INCOIS_API_KEY`). | Built-in GeoJSON bulletin parser and ingestion worker operational with graceful fallback when key is not configured. | **VERIFIED** (Non-blocking graceful fallback) |

---

## 3. CMFRI Data Acquisition Package & Requisition Workflow

### 3.1 Pilot Landing Centers & Scope
1. **Malim Jetty / Panaji (Goa):** Latitude $15.5036^\circ\text{N}$, Longitude $73.8286^\circ\text{E}$ (Trawlers, Purse Seiners)
2. **Mirkarwada / Ratnagiri (Maharashtra):** Latitude $16.9902^\circ\text{N}$, Longitude $73.2847^\circ\text{E}$ (Trawlers, Gillnetters)
3. **Sasoon Docks / Colaba (Mumbai):** Latitude $18.9167^\circ\text{N}$, Longitude $72.8250^\circ\text{E}$ (Mechanized Multi-day Trawlers)
4. **Karwar / Baithkol (Karnataka):** Latitude $14.8055^\circ\text{N}$, Longitude $74.1244^\circ\text{E}$ (Purse Seiners, Trawlers)
5. **Mangalore / Old Port (Karnataka):** Latitude $12.8580^\circ\text{N}$, Longitude $74.8360^\circ\text{E}$ (Purse Seiners, Longliners, Trawlers)

### 3.2 Target Species (CMFRI / FAO)
- **Indian Mackerel** (*Rastrelliger kanagurta*, FAO: `RAK`)
- **Oil Sardine** (*Sardinella longiceps*, FAO: `IOS`)
- **Skipjack Tuna** (*Katsuwonus pelamis*, FAO: `SKJ`)
- **Yellowfin Tuna** (*Thunnus albacares*, FAO: `YFT`)
- **Silver Pomfret** (*Pampus argenteus*, FAO: `POA`)

### 3.3 Requisition Specifications
- **Target Temporal Window:** January 1, 2023 to December 31, 2025 (Monthly / Trip-level aggregations).
- **Required Data Fields:** Landing Center Name, Date of Landing, Voyage Duration (Hours), Fishing Gear Type, Target Species, Catch Weight (kg), CPUE (kg/hour), Estimated Fishing Zone Coordinates / Grid Cell.
- **Licensing & Attribution:** Academic / Research Evaluation License citing ICAR-CMFRI National Marine Fisheries Data Centre (NMFDC).
- **Outstanding Methodological Inquiries:**
  - Standardized gear adjustment factors between purse seine and mechanized trawl effort.
  - Recording protocol for zero-catch exploratory voyages.
  - Multi-species catch allocation during single commercial trawling operations.
- **Submission Status:** **`PREPARED_FOR_SUBMISSION`** (Documented and ready; not yet submitted, approved, or fulfilled).

---

## 4. Verification and Regression Summary

All tests executed sequentially:
- **Targeted Unit Tests (v2.8):** 5 / 5 passed (0.13s)
- **Full Backend Suite (pytest):** 292 / 292 passed (0 failures)
- **Frontend Integration Suite:** 34 / 34 passed (27s)
- **Frontend Linter:** 0 errors across 16 files
- **Production Build:** Success in 135ms
- **Browser Automation Suite:** 21 / 21 checks passed
