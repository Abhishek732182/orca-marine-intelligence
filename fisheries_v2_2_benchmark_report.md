# ORCA Fisheries Intelligence v2.2 — Validation Benchmark Report

**Benchmark Version:** v2.2  
**Dataset Reference:** `data/benchmarks/fisheries_v2_2_benchmark.json`  
**Reference Clock (UTC):** `2026-10-12T04:00:00Z`  
**Tolerance Parameters:** Clock Skew $\le$ 300 s (5 min), Spatial Mismatch $\le$ 50.0 km  
**Evaluator Engine:** [backend/app/evaluation/fisheries_benchmark.py](file:///d:/orca/backend/app/evaluation/fisheries_benchmark.py)

---

## 1. Executive Summary & Scientific Findings

The ORCA v2.2 Fisheries Validation Benchmark establishes a deterministic, reproducible evaluation pipeline that rigorously distinguishes **environmental habitat suitability** from **confirmed biological fish presence**.

### Key Findings:
1. **Biological Ground-Truth Absence:**  
   Zero verified in-situ biological presence/absence ground-truth telemetry records (acoustic biomass, commercial landing registers, scientific pelagic trawls) exist in the operational repository or connected live feeds.
2. **Predictive Accuracy Integrity:**  
   In compliance with ORCA scientific integrity guarantees and directive 6, **predictive classification accuracy (Precision, Recall, F1, calibration) is explicitly marked `not_evaluable`**. Accuracy scores were NOT fabricated or approximated from synthetic distributions.
3. **Environmental Rule Consistency (100.0%):**  
   All 5 evaluated operational marine stations across the Arabian Sea (Goa, Mumbai, Karwar, Mangalore, Veraval) demonstrated 100% compliance with documented CMFRI/FAO species thermal preferences.
4. **Safeguard Robustness (100.0% Measured Rate):**  
   Every challenge case in the `safeguard_challenge` partition passed all defense criteria: temporal leakage was blocked, spatial mismatches ($> 50$ km) were quarantined, stale satellite observations were excluded from scoring, conflicting duplicates were flagged without cherry-picking, and offline fixture advisories were barred from the operational baseline.

---

## 2. Dataset Counts and Partition Provenance

The versioned benchmark dataset contains three strictly isolated partitions:

| Partition | Record Count | Data Origin & Provenance | Primary Operational Baseline Eligible? |
|---|---|---|---|
| **`verified_environmental`** | 5 stations (15 observations) | Real station coordinates across Arabian Sea with Open-Meteo physical waves, Open-Meteo SST, and NOAA ERDDAP VIIRS chlorophyll-a. Explicitly lacks biological labels (`biological_presence_label: null`). | **Yes** |
| **`offline_fixture_catalog`** | 2 advisories | Static INCOIS sample bulletin (`INCOIS-PFZ-GOA-2026-10-12`) tagged with quality flags `offline_fixture`, `is_offline_fixture: True`. | **No (Barred from baseline)** |
| **`safeguard_challenge`** | 7 controlled challenge cases | Synthetic edge cases explicitly labeled `is_synthetic: True` covering future timestamps, retrieval inversion, spatial drift, duplicate conflicts, 48h stale passes, and fixture injection. | **No (Safeguard testing only)** |

---

## 3. Coverage & Rule Consistency Metrics

| Metric ID | Metric Name | Category | Numerator / Denominator | Measured Value | Evaluation Status | Interpretation |
|---|---|---|---|---|---|---|
| `cov_wave_sst` | Wave and SST Evidence Coverage | Coverage | 5 / 5 | **100.0%** | `evaluated` | All 5 stations possess valid, non-stale wave height and SST observations. |
| `cov_chlorophyll_a` | Usable Chlorophyll-a Coverage | Coverage | 5 / 5 | **100.0%** | `evaluated` | All 5 stations possess non-cloud-masked, fresh satellite ocean color. |
| `cov_biological_telemetry` | Verified Biological Evidence Coverage | Coverage | 0 / 5 | **0.0%** | `evaluated` | **0.0% coverage.** In-situ biological fish telemetry is absent in operational feeds. |
| `rule_consistency_species` | Species Environmental Rule Consistency | Rule Consistency | 5 / 5 | **100.0%** | `evaluated` | 100% of species evaluations conform to documented CMFRI/FAO thermal preferences. |
| `acc_biological_classification` | Biological Presence Precision / Recall / F1 | Accuracy | 0 / 0 | **None** | `not_evaluable` | **NOT EVALUABLE.** Ground-truth labels are absent; metrics withheld to prevent false accuracy claims. |

---

## 4. Safeguard Defense Results

| Safeguard Metric ID | Tested Defense Mechanism | Challenge Cases | Quarantined / Rejected | Measured Defense Rate | Target Objective | Status |
|---|---|---|---|---|---|---|
| `safeguard_temporal_leakage` | Future timestamps & observation after retrieval | 2 | 2 | **100.0%** | 100.0% | **PASSED** |
| `safeguard_spatial_mismatch` | Observations diverging $> 50$ km from query ($441.9$ km) | 1 | 1 | **100.0%** | 100.0% | **PASSED** |
| `safeguard_stale_exclusion` | Satellite observations older than 24h freshness window | 1 | 1 | **100.0%** | 100.0% | **PASSED** |
| `safeguard_duplicate_conflict` | Co-located conflicting duplicates ($28.5^\circ\text{C}$ vs $21.0^\circ\text{C}$) | 1 | 1 | **100.0%** | 100.0% | **PASSED** |
| `safeguard_fixture_contamination` | Offline fixture catalog records attempting baseline entry | 3 | 3 | **100.0%** | 100.0% | **PASSED** |

### Duplicate Conflict Resolution Guarantee:
Neither favorable ($28.5^\circ\text{C}$) nor unfavorable ($21.0^\circ\text{C}$) was cherry-picked. Both records were flagged as `FLAGGED_CONFLICT_QUARANTINED` with `cherry_picked: False`.

---

## 5. Limitations & Follow-Up Requirements

1. **Absence of Biological Presence Data:**  
   Current operational integrations are limited to physical wave models (Open-Meteo), numerical sea surface temperature (Open-Meteo), and satellite ocean color (NOAA ERDDAP VIIRS). Acoustic sonar surveys and commercial fish catch landing registers are not connected.
2. **Operational Scope:**  
   High suitability scores represent favorable **oceanographic habitat parameters** (thermal and trophic conditions), which must never be conflated with confirmed fish presence or vessel clearance.
3. **Follow-Up Data Requirements:**  
   To enable genuine classification accuracy, Precision, Recall, and F1 evaluation, authenticated commercial catch landing logs (e.g. CMFRI Marine Fisheries Information Series) or acoustic pelagic trawl surveys must be ingested with verified spatial coordinates, target species identification, and timestamped catch weights.
