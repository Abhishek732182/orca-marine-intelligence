# ORCA Fisheries Intelligence v2.7 — Final Remaining Work & Issue Inventory Report

**Document Version:** 2.7.0  
**Pilot Target Area:** Eastern Arabian Sea Corridor (Goa, Malim, Ratnagiri, Mumbai, Karwar, Mangalore)  
**Accepted Baseline:** v2.6  
**Final Baseline:** v2.7  
**Operational Biological Store Status:** `AWAITING_AUTHORIZED_DATA`  

---

## 1. Executive Summary

ORCA v2.7 represents the comprehensive audit, hardening, and verification milestone for the ORCA Marine Intelligence & Fishing Advisory Platform. In this milestone:
1. **Repository Audit:** A full audit of all backend data sources, specialist agents, LangGraph orchestrator, evidence schemas, validation benchmarks, and frontend components was conducted.
2. **Defect Remediation:** Six confirmed internal defects were identified and resolved with minimal, targeted, evidence-backed fixes.
3. **Data Invariance & Zero Fabrication:** In the absence of an authorized external CSV file in the repository, the operational biological evidence store was left completely empty (`AWAITING_AUTHORIZED_DATA`). No synthetic catches, mock labels, or speculative accuracies were fabricated.
4. **End-to-End Verification:** All six test layers (targeted unit tests, full backend suite, frontend live integration tests, linter, production build, and headless Google Chrome browser suite) were independently executed and passed with 100% success.

---

## 2. Issue Inventory: Confirmed Internal Defects & Remediation

| Issue ID | Severity | Component / File | Evidence & Root Cause | Implemented Fix | Verification Outcome |
| :---: | :---: | :--- | :--- | :--- | :---: |
| **ORCA-V27-01** | **HIGH** | `backend/app/data_sources/biological_adapter.py` | `self._normalized_records.append(ev_rec)` was called unconditionally in `normalize_record()`, mutating the adapter store even when `is_dry_run=True`. | Added `commit: bool = True` parameter to `AuthorizedFisheriesAdapter.normalize_record()`. Store append is gated on `if commit:`. `GroundTruthCsvImporter` passes `commit=False` during dry runs. | **PASSED** (Store count verified 0 after dry run) |
| **ORCA-V27-02** | **MEDIUM** | `backend/app/data_sources/biological_adapter.py` & `ground_truth_import.py` | Python's `float("nan")` and `float("inf")` parse strings without raising `ValueError`, bypassing bounds checks (`nan > 50.0` is `False`). | Added explicit `math.isnan()` and `math.isinf()` checks on latitude, longitude, spatial uncertainty, catch weight, and effort hours. Rejects with explicit codes (`coordinates_nan_or_infinite`, `catch_weight_nan_or_infinite`, `effort_hours_nan_or_infinite`). | **PASSED** (Targeted unit tests confirm rejection) |
| **ORCA-V27-03** | **MEDIUM** | `backend/app/data_sources/ground_truth_import.py` | Ingested records and summaries lacked source file SHA256 checksums, preventing forensic provenance tracking. | Implemented SHA256 file hashing (`hashlib.sha256(content.encode('utf-8')).hexdigest()`), recorded in `GroundTruthImportSummary.source_file_sha256` and injected into `EvidenceRecord.metadata["source_file_sha256"]`. | **PASSED** (64-character hex hash verified in record metadata) |
| **ORCA-V27-04** | **MEDIUM** | `backend/app/data_sources/ground_truth_import.py` | Re-importing the same authorized file risked duplicate record generation and lacked store before/after integrity tracking. | Added `self.imported_file_checksums: set[str]`, `store_count_before`, `store_count_after`, and `is_idempotent_reimport` logic. Re-importing identical checksums skips duplicate insertion idempotently. | **PASSED** (Second import skipped with store count unchanged) |
| **ORCA-V27-05** | **HIGH** | `backend/app/data_sources/ground_truth_import.py` | In `BiologicalDataQualityGate`, `seen_signatures` was permanently updated during dry runs, causing subsequent actual imports to be falsely rejected as `duplicate_record_detected`. | Implemented dry-run snapshotting and rollback of `seen_signatures`. Dry run cleans up signature state so subsequent live imports succeed seamlessly. | **PASSED** (Live import after dry run succeeds with accepted count 1) |
| **ORCA-V27-06** | **LOW** | `backend/app/agents/species_rules.py` | Fifth prioritized CMFRI pilot species (**Silver Pomfret**, *Pampus argenteus*) was missing from `SPECIES_REGISTRY`. | Formally added `pomfret` / `Silver Pomfret` (*Pampus argenteus*, FAO: `POA`, Family: *Stromateidae*) with documented SST preferences ($25.0^\circ\text{C} - 29.5^\circ\text{C}$ optimal) and CMFRI citation. | **PASSED** (All 5 CMFRI species parse and evaluate thermally) |

---

## 3. External Dependencies & Operational Blockers

The following external dependencies were verified as genuine external factors:

| Dependency | Responsible Institution | Current Operational Status | Impact on ORCA Subsystems |
| :--- | :--- | :--- | :--- |
| **Authorized Ground-Truth Landing Statistics** | ICAR-CMFRI, Kochi (FRAEED / FCSC) | **Pending Formal Data Requisition** | Operational store remains empty (`AWAITING_AUTHORIZED_DATA`). Model evaluation metrics remain `NOT_EVALUABLE`. |
| **Live Satellite Chlorophyll-a (Clear-Sky)** | NOAA CoastWatch / VIIRS | **100% Cloud-Masked over Arabian Sea** | ERDDAP returns HTTP 200 with 100% null grid cells. Usable fresh coverage is legitimately 0.0% under 24h freshness policy. |
| **INCOIS PFZ Automated Production Feed** | INCOIS (MoES), Hyderabad | **Awaiting Production API Key** | Offline bulletin parser works; live feed requires `API_KEY_ORCA_INCOIS_PROD`. |

---

## 4. Changed Files Summary

1. [`backend/app/data_sources/biological_adapter.py`](file:///d:/orca/backend/app/data_sources/biological_adapter.py):
   - Added `import math`.
   - Added `math.isnan()` and `math.isinf()` checks to `BiologicalDataQualityGate.validate_record()`.
   - Added `commit: bool = True` to `AuthorizedFisheriesAdapter.normalize_record()`.
2. [`backend/app/data_sources/ground_truth_import.py`](file:///d:/orca/backend/app/data_sources/ground_truth_import.py):
   - Added `import hashlib` and `import math`.
   - Added `source_file_sha256`, `store_count_before`, `store_count_after`, and `is_idempotent_reimport` to `GroundTruthImportSummary`.
   - Added `imported_file_checksums` tracking, idempotent re-import detection, and failure rollback to `GroundTruthCsvImporter`.
   - Added NaN/Inf coordinate, catch, and effort validation in row processing.
   - Added dry-run `commit=False` and signature rollback to prevent dry runs from polluting or locking subsequent imports.
3. [`backend/app/agents/species_rules.py`](file:///d:/orca/backend/app/agents/species_rules.py):
   - Registered Silver Pomfret (*Pampus argenteus*, FAO: `POA`) in `SPECIES_REGISTRY`.
4. [`tests/unit/test_fisheries_hardening_v2_7.py`](file:///d:/orca/tests/unit/test_fisheries_hardening_v2_7.py):
   - Created 8 targeted unit tests covering NaN/Inf rejection, idempotent imports, dry-run rollback, checksum injection, store count tracking, Pomfret species rules, and ERDDAP null tables.
5. [`tests/unit/test_ground_truth_import_v2_5.py`](file:///d:/orca/tests/unit/test_ground_truth_import_v2_5.py):
   - Expanded unit suite to 16 tests covering all five CMFRI pilot species, five landing centers, and operational store invariance.

---

## 5. Next Required Action

- **Dispatch Acquisition Package:** Formally submit the compiled CMFRI data acquisition package (documented in `fisheries_v2_7_pilot_readiness_report.md`) to the Director, ICAR-CMFRI, Kochi, to secure 2023–2025 West Coast landing statistics under the ICAR Data Access Policy.
