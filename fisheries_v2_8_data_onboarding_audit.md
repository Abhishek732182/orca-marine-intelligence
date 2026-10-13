# ORCA Fisheries Intelligence v2.8 — Data Onboarding Audit & CMFRI Readiness Report

**Document Version:** 2.8.0  
**Pilot Target Area:** Eastern Arabian Sea Corridor (Goa, Malim, Ratnagiri, Mumbai, Karwar, Mangalore)  
**Accepted Baseline:** v2.7  
**Current Baseline:** v2.8  
**Operational Biological Store Status:** `AWAITING_AUTHORIZED_DATA`  
**Classification:** `SOFTWARE_DEMO_READY` / `AWAITING_AUTHORIZED_DATA`  

---

## 1. Executive Summary

This report delivers the comprehensive audit of ORCA v2.8's ground-truth biological data onboarding pipeline and formalizes the acquisition framework for authorized 2023–2025 commercial landing statistics from ICAR-CMFRI, Kochi.

Key conclusions of this audit:
1. **CMFRI Requisition Package Formalized:** The official submission package ([CMFRI_DATA_REQUISITION_PACKAGE_v2_8.md](file:///D:/orca/CMFRI_DATA_REQUISITION_PACKAGE_v2_8.md)) has been finalized with an executive checklist, formal letter draft to the CMFRI Director, technical annexures, and institutional contact details.
2. **Species Reconciliation Completed:** Inconsistencies across prior releases were resolved without silent substitutions. The 5 priority commercial species (Indian Mackerel, Indian Oil Sardine, Yellowfin Tuna, Skipjack Tuna, Silver Pomfret) plus demersal reference (Bombay Duck) are mapped to their international FAO 3-alpha codes (`RAK`, `IOS`, `YFT`, `SKJ`, `POA`, `DUC`) and scientific binomials, with clear requests for CMFRI to confirm their preferred coding convention.
3. **Importer Verification & Provenance:** The ground-truth importer was verified across 40 unit tests using isolated test fixtures. Ingestion dry-run mode preserves store contents and duplicate detection state, and records SHA256 checksums in evidence metadata.
4. **Zero Data Fabrication Maintained:** The operational biological store contains **0 records** (`AWAITING_AUTHORIZED_DATA`). No test fixtures, synthetic catch logs, or speculative occurrences have been committed to operational memory or disk.
5. **Prediction Metrics Withheld:** Biological prediction accuracy remains **`NOT_EVALUABLE`** until independent authorized labels are received and evaluated.

---

## 2. CMFRI Requisition Verification: Scope & Specifications

The formal requisition package verifies and includes all required specifications:

### 2.1 Five Strategic Pilot Landing Centers
1. **Malim Jetty / Panaji (Goa):** Latitude $15.5036^\circ\text{N}$, Longitude $73.8286^\circ\text{E}$ (Purse Seiners, Mechanized Trawlers)
2. **Mirkarwada / Ratnagiri (Maharashtra):** Latitude $16.9902^\circ\text{N}$, Longitude $73.2847^\circ\text{E}$ (Trawlers, Gillnetters, Ring Seiners)
3. **Sasoon Docks / Colaba (Mumbai, Maharashtra):** Latitude $18.9167^\circ\text{N}$, Longitude $72.8250^\circ\text{E}$ (Multi-day Deep-sea Trawlers)
4. **Baithkol / Karwar (Karnataka):** Latitude $14.8055^\circ\text{N}$, Longitude $74.1244^\circ\text{E}$ (Purse Seiners, Motorized Crafts)
5. **Mangalore Old Port (Karnataka):** Latitude $12.8580^\circ\text{N}$, Longitude $74.8360^\circ\text{E}$ (Purse Seiners, Longliners, Trawlers)

### 2.2 Target Period & Granularity
- **Target Period:** January 1, 2023 – December 31, 2025.
- **Granularity Requested:** Trip-level catch logs preferred; monthly landing aggregations acceptable if trip-level data is restricted under data-privacy policies.

### 2.3 Required Data Fields & Units
- Mandatory: `record_identifier`, `source_agency`, `dataset_identifier`, `observation_method`, `species_name`, `latitude`, `longitude`, `observed_at` (ISO 8601 UTC), `catch_weight` (kg), `catch_unit` ("kg"), `effort_value` (hours), `effort_unit` ("hours"), `is_authorized` (true).
- Optional Contextual: `scientific_name`, `fao_alpha3_code`, `spatial_uncertainty_km`, `landing_center_name`, `gear_type`, `voyage_start_at`, `voyage_end_at`.

### 2.4 Effort & CPUE Definitions
- **Catch:** Total landed weight in kilograms ($\text{kg}$).
- **Effort:** Cumulative active fishing/trawl duration in hours ($\text{hours}$).
- **CPUE Formula:**
  $$\text{CPUE} = \frac{\text{catch\_weight\_kg}}{\text{effort\_hours}} \quad (\text{kg/hour})$$
- Aggregated trip records lacking explicit fishing hours cannot be used to infer individual-voyage CPUE without documented conversion multipliers.

---

## 3. Cross-Version Species Reconciliation & Code Resolution

Prior project releases exhibited minor nomenclature differences regarding target species and taxonomic codes. This reconciliation clarifies the status of all species:

| Common Name | Scientific Binomial | FAO Code | Software Key | Optimal SST | Release History & Status |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Indian Mackerel** | *Rastrelliger kanagurta* | `RAK` | `mackerel` | $26.0^\circ\text{C} - 30.0^\circ\text{C}$ | Core pelagic species across all releases (v2.1–v2.8). Standard indicator. |
| **Indian Oil Sardine** | *Sardinella longiceps* | `IOS` | `sardine` | $27.0^\circ\text{C} - 30.0^\circ\text{C}$ | Core pelagic species across all releases (v2.1–v2.8). Upwelling indicator. |
| **Yellowfin Tuna** | *Thunnus albacares* | `YFT` | `tuna` | $24.0^\circ\text{C} - 29.0^\circ\text{C}$ | Grouped under `tuna` in early versions. Requested as separate code `YFT`. |
| **Skipjack Tuna** | *Katsuwonus pelamis* | `SKJ` | `tuna` | $24.0^\circ\text{C} - 28.5^\circ\text{C}$ | Aliased under `tuna` in early versions. Requested as separate code `SKJ`. |
| **Silver Pomfret** | *Pampus argenteus* | `POA` | `pomfret` | $25.0^\circ\text{C} - 29.5^\circ\text{C}$ | Formally integrated in v2.7. Dominant West Coast neritic commercial finfish. |
| **Bombay Duck** | *Harpadon nehereus* | `DUC` | `bombay duck`| $25.0^\circ\text{C} - 29.0^\circ\text{C}$ | Retained in registry as historical demersal baseline for Mumbai/Ratnagiri. |

### Technical Reconciliation in Software
1. Added `"fao_code"` and lowercase FAO alpha-3 codes (`rak`, `ios`, `yft`, `skj`, `poa`, `duc`) to `aliases` in `SPECIES_REGISTRY` ([species_rules.py](file:///D:/orca/backend/app/agents/species_rules.py)).
2. Enhanced `lookup_species()` to match against FAO alpha-3 codes directly, returning `SUPPORTED` and resolving the standard common name.
3. Enhanced `COLUMN_ALIASES` in [ground_truth_import.py](file:///D:/orca/backend/app/data_sources/ground_truth_import.py) to parse `fao_alpha3_code` from incoming CSV columns and forward it to `RawBiologicalFisheriesRecord`.

---

## 4. Importer Verification & Safety Audit

The ground-truth import workflow was verified against strict safety and integrity criteria:

| Safety Gate | Verification Mechanism | Audit Result |
| :--- | :--- | :---: |
| **Dry-Run Store Invariance** | Dry run validates all rows and reason codes without committing to `_normalized_records`. | **VERIFIED** (Store count = 0 after dry run) |
| **Dry-Run Signature Rollback** | Quality gate snapshot-and-rollback ensures dry-run signatures do not block subsequent live imports. | **VERIFIED** (Live import succeeds after dry-run) |
| **SHA256 File Checksum Provenance** | Importer computes SHA256 of raw CSV content and records it in `summary.source_file_sha256` and `record.metadata`. | **VERIFIED** (64-char hex hash preserved) |
| **Idempotent Re-Import** | Second ingestion of identical file SHA256 is detected and skipped without duplicating records. | **VERIFIED** (Store count unchanged on re-import) |
| **Unauthorized Quarantine** | Unofficial records (`is_authorized=false`) marked `status="invalid"` and excluded from operational store. | **VERIFIED** (Never committed to store) |
| **NaN / Inf Bounds Protection** | Explicit rejection of `NaN` or `Infinity` in coordinates, spatial uncertainty, catch weight, and effort hours. | **VERIFIED** (Explicit reason codes generated) |
| **BOM Header Handling** | Strips UTF-8 Byte Order Mark (`\ufeff`) preventing unmapped column rejections on Windows exports. | **VERIFIED** (BOM headers resolved seamlessly) |
| **Negative Bounds Protection** | Rejects negative distance, negative catch weight, and non-positive effort hours upfront. | **VERIFIED** (Explicit reason codes generated) |

---

## 5. Test Execution & Regression Evidence

The ground-truth import and fisheries adapter test suites were executed:

```powershell
D:\orca\.venv\Scripts\pytest.exe tests/unit/test_ground_truth_import_v2_5.py tests/unit/test_fisheries_adapter_v2_4.py tests/unit/test_fisheries_hardening_v2_7.py tests/unit/test_fisheries_hardening_v2_8.py -v
```

**Results:**
- `test_ground_truth_import_v2_5.py`: 16 passed
- `test_fisheries_adapter_v2_4.py`: 10 passed
- `test_fisheries_hardening_v2_7.py`: 8 passed
- `test_fisheries_hardening_v2_8.py`: 6 passed
- **Total Ground-Truth Tests:** **40 / 40 passed in 0.16s (100% pass rate)**

---

## 6. Current Operational Store State & External Dependencies

- **Operational Store Records:** `0`
- **Current Operational Store Status:** `AWAITING_AUTHORIZED_DATA`
- **Chlorophyll-a Usable Fresh Coverage:** `0.0%` (24-hour freshness policy strictly enforced; persistent cloud masking in VIIRS passes).
- **Biological Prediction Metrics:** `NOT_EVALUABLE` (withheld until authorized ground-truth labels are available).

### Unresolved External Dependencies
1. **CMFRI Requisition Signoff & Transmission:** Submission of [CMFRI_DATA_REQUISITION_PACKAGE_v2_8.md](file:///D:/orca/CMFRI_DATA_REQUISITION_PACKAGE_v2_8.md) by the Project Principal Investigator to the Director, ICAR-CMFRI, Kochi.
2. **Institutional Data Delivery:** Formal receipt and release of the 2023–2025 commercial landing statistics dataset.
3. **Clear-Sky Satellite Coverage:** Cloud-free passes required before live satellite chlorophyll-a observations become usable over the Eastern Arabian Sea corridor.
4. **INCOIS API Credentials:** Institutional `INCOIS_API_KEY` required for automated PFZ bulletin polling.

---

## 7. Pilot Readiness Classification

$$\mathbf{SOFTWARE\_DEMO\_READY} \quad \text{and} \quad \mathbf{AWAITING\_AUTHORIZED\_DATA}$$

The project is fully prepared to ingest and validate the first authorized biological dataset immediately upon receipt.
