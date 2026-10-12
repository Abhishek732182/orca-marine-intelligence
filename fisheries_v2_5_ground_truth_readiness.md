# ORCA Fisheries Intelligence v2.5 — Ground-Truth Acquisition & Benchmark Readiness

**Document Version:** 2.5.0  
**Target Pilot:** Eastern Arabian Sea / West Coast Indian EEZ (Goa, Malim, Ratnagiri, Mumbai, Karwar, Mangalore)  
**System Architecture:** Python 3.13 / FastAPI Marine Intelligence Core  
**Standard Compliance:** Darwin Core (DwC), FAO Fisheries Statistics Standards (CWP), ORCA Evidence Schema v2.1/v2.4/v2.5  

---

## 1. Executive Summary & Repository Audit

ORCA v2.5 advances the fisheries intelligence subsystem to **Ground-Truth Acquisition & Benchmark Readiness**. Building directly upon the accepted v2.4 baseline:
1. **Preservation of Core Architecture:** Zero modifications to existing API contracts, agent schemas, or the six-agent architecture (`WeatherAgent`, `OceanAgent`, `FishingZoneAgent`, `RouteAgent`, `SafetyRiskAgent`, `OrchestratorAgent`). No new agent was introduced.
2. **Reuse of Core Foundations:** Reuses `AuthorizedFisheriesAdapter`, `BiologicalDataQualityGate`, `RawBiologicalFisheriesRecord`, and `BiologicalObservationMethod` from `backend/app/data_sources/biological_adapter.py`.
3. **Offline CSV Ingestion Contract:** Implemented `GroundTruthCsvImporter` in [`backend/app/data_sources/ground_truth_import.py`](file:///d:/orca/backend/app/data_sources/ground_truth_import.py) to ingest and validate offline exports from ICAR-CMFRI and FSI without creating live unverified HTTP endpoints.
4. **Benchmark Leakage Prevention:** Implemented `BenchmarkPartitionValidator` to guarantee zero duplicate leakage (cross-split signature collisions) and zero temporal leakage (evaluation observations strictly post-dating training cutoff).
5. **Chlorophyll Satellite Freshness Policy:** Maintained strict adherence to the 24-hour freshness rule. Live satellite chlorophyll usable coverage remains confirmed at **0.0%** due to persistent cloud cover and stale orbital passes.
6. **Scientific Prediction Boundary:** Model prediction accuracy metrics (Precision, Recall, F1, AUC-ROC) remain strictly **`NOT_EVALUABLE`**. Ground-truth biological labels are not yet present in the operational repository; accuracy will not be evaluated on unverified or fabricated data.

---

## 2. Distinction of Reality: Implemented Code, Verified Access, Tests & Blockers

To maintain scientific integrity, the boundary between what is implemented, what is verified, and what is pending is explicitly categorized:

| Category | Status | Details |
| :--- | :--- | :--- |
| **Implemented Functionality** | **Production-Ready (Offline)** | `GroundTruthCsvImporter`, canonical schema validator, header alias resolver, unit compatibility gate, CPUE derivation engine, dry-run diagnostic mode, `BenchmarkPartitionValidator`, and chlorophyll freshness link validator. |
| **Verified Source Access** | **Pending Official Credentials** | No live API credentials or direct database connections are currently active. CMFRI and FSI feeds remain categorized as **OFFLINE / PENDING AUTHORIZATION**. No live endpoints have been fabricated. |
| **Simulated Test Cases** | **Deterministic In-Memory Fixtures** | 14 unit test fixtures in `tests/unit/test_ground_truth_import_v2_5.py` and 10 in `tests/unit/test_fisheries_adapter_v2_4.py` test edge cases (empty files, malformed headers, invalid coordinates, future dates, incompatible units, duplicate leakage) strictly in memory. |
| **Outstanding External Dependencies** | **External Institutional Action** | Formal data requisition letter and Non-Disclosure Agreement (NDA) with Director, ICAR-CMFRI, Kochi; access to ICAR KRISHI Geo-Portal bulk data exports. |

---

## 3. CMFRI Data-Request Checklist

The following checklist details the exact administrative and technical parameters required for the official data acquisition submission to the Central Marine Fisheries Research Institute (ICAR-CMFRI), Kochi:

### A. Administrative Requisition Details
- [ ] **Target Custodian:** The Director, Central Marine Fisheries Research Institute (ICAR-CMFRI), Post Box No. 1603, Ernakulam North P.O., Kochi - 682 018, Kerala, India.
- [ ] **Data Division:** Fishery Resources Assessment, Economics & Extension Division (FRAEED) / Fish Catch Survey Coordination (FCSC).
- [ ] **Project Context:** ORCA Marine Intelligence — Navigation Safety, Fuel Conservation & Artisanal Fisheries Decision Support System.
- [ ] **Institutional Agreement:** Execution of ICAR Standard Data Sharing Agreement & Academic/Industrial Research NDA.
- [ ] **Export Format Requested:** Machine-readable CSV or Parquet export containing trip-level or harbor landing records.

### B. Target Pilot Landing Centers (Eastern Arabian Sea Corridor)
- [ ] **Malim Jetty & Panaji** (Goa): $15.503^\circ\text{N}, 73.827^\circ\text{E}$ (Purse-seine and motorized gillnet landings)
- [ ] **Mirkarwada Fishing Harbour** (Ratnagiri, Maharashtra): $16.985^\circ\text{N}, 73.280^\circ\text{E}$ (Trawl and purse-seine pelagic landings)
- [ ] **Sasoon Docks & New Ferry Wharf** (Mumbai, Maharashtra): $18.915^\circ\text{N}, 72.825^\circ\text{E}$ (Multi-day mechanized trawlers)
- [ ] **Karwar Baitkhol Harbour** (Karnataka): $14.805^\circ\text{N}, 74.120^\circ\text{E}$ (Coastal neritic mackerel/sardine landings)
- [ ] **Mangalore Old Port** (Karnataka): $12.860^\circ\text{N}, 74.835^\circ\text{E}$ (Deep-water oceanic and neritic landings)

### C. Target Species & Taxonomic Codes
- [ ] **Indian Mackerel** (*Rastrelliger kanagurta*) — FAO Alpha-3: `RAK`, AphiaID: `219806`
- [ ] **Indian Oil Sardine** (*Sardinella longiceps*) — FAO Alpha-3: `OIL`, AphiaID: `219961`
- [ ] **Yellowfin Tuna** (*Thunnus albacares*) — FAO Alpha-3: `YFT`, AphiaID: `127027`
- [ ] **Silver Pomfret** (*Pampus argenteus*) — FAO Alpha-3: `POA`, AphiaID: `219965`
- [ ] **Bombay Duck** (*Harpadon nehereus*) — FAO Alpha-3: `BOD`, AphiaID: `219963`

---

## 4. Proposed CSV / Schema Specification

The offline import contract expects a CSV structure adhering to Darwin Core and FAO CWP standards. The importer supports both canonical headers and documented CMFRI/FSI aliases.

### A. Column Specification Table

| Canonical Column | Data Type | Nullable | Accepted Aliases | Description & Validation Criteria |
| :--- | :--- | :--- | :--- | :--- |
| `record_identifier` | String | No | `record_id`, `haul_id`, `trip_id`, `landing_id` | Unique primary key of the observation or survey haul. |
| `source_agency` | String | No | `agency`, `institution`, `source`, `custodian` | Statutory authority, e.g. `ICAR-CMFRI` or `FSI`. |
| `dataset_identifier` | String | No | `dataset_id`, `survey_id`, `batch_id` | Identifier of dataset or survey batch. |
| `observation_method` | String | No | `method`, `sampling_protocol`, `observation_type` | Must match `COMMERCIAL_LANDING_STATISTIC`, `SCIENTIFIC_RESEARCH_TRAWL`, etc. |
| `species_name` | String | No | `species_raw_name`, `species`, `common_name` | Common or vernacular name, validated against `SPECIES_REGISTRY`. |
| `scientific_name` | String | Yes | `scientificname`, `taxon` | Binomial Latin taxonomic name. |
| `latitude` | Float | No | `lat`, `decimallatitude` | Decimal latitude $[-90.0, 90.0]$. |
| `longitude` | Float | No | `lon`, `long`, `decimallongitude` | Decimal longitude $[-180.0, 180.0]$. |
| `spatial_uncertainty_km` | Float | Yes | `uncertainty_km`, `spatial_uncertainty` | Coordinate uncertainty radius; defaults to $5.0\text{ km}$; max threshold $50.0\text{ km}$. |
| `landing_center_name` | String | Yes | `landing_center`, `harbour`, `port`, `landing_site` | Name of landing center or survey port. |
| `observed_at` | String | No | `event_date`, `landing_date`, `haul_time`, `date` | ISO 8601 UTC timestamp. Cannot be in future relative to clock. |
| `voyage_start_at` | String | Yes | `voyage_start`, `departure_time` | Departure timestamp; must precede or equal `observed_at`. |
| `voyage_end_at` | String | Yes | `voyage_end`, `arrival_time` | Arrival timestamp; must follow or equal `observed_at`. |
| `catch_weight` | Float | No | `catch_weight_kg`, `catch_kg`, `catch` | Numeric catch weight ($\ge 0.0\text{ kg}$). |
| `catch_unit` | String | No | `unit_catch`, `catch_units` | Must be `kg`, `kilogram`, or `kilograms`. |
| `effort_value` | Float | No | `effort`, `effort_hours`, `duration_hours` | Numeric sampling or fishing effort ($> 0.0$). |
| `effort_unit` | String | No | `unit_effort`, `effort_units` | Must be `hours`, `h`, `hour`, `trawl_hours`, or `fishing_hours`. |
| `gear_type` | String | Yes | `gear`, `fishing_gear` | Commercial or research gear (e.g. `Purse Seine`, `Pelagic Trawl`). |
| `is_authorized` | Boolean | No | `authorized`, `is_authorized_official_feed` | `true`/`false`. If `false`, record is quarantined as `unverified_data_feed`. |
| `access_authorization_token`| String | Yes | `auth_token`, `token`, `license_key` | Valid institutional credential or license key. |

### B. Catch Per Unit Effort (CPUE) Derivation Formula
Catch Per Unit Effort is computed strictly when valid catch weight and effort hours are present:
$$\text{CPUE} = \frac{\text{catch\_weight\_kg}}{\text{effort\_hours}} \quad \left(\frac{\text{kg}}{\text{hour}}\right)$$

If incompatible effort units (e.g. `days`, `trips`, `nets`) or catch units (e.g. `boxes`, `baskets`) are provided without standardized conversion factors, the row is rejected with `incompatible_effort_units` or `incompatible_catch_units`. Missing values are never silently fabricated.

---

## 5. Benchmark-Readiness Report

### A. Missing Fields & Ground-Truth Telemetry Gaps
1. **Absence / Zero-Catch Hauls:** Commercial landing statistics from harbor jetty logbooks only report landed fish ($W > 0$). They systematically omit zero-catch fishing events (true negatives). Research vessel exploratory trawls from FSI are required to populate verified absence ground truth.
2. **Tow-Level High-Precision Geolocation:** Commercial landings reflect catches aggregated across vessels operating anywhere within 10–50 nautical miles of the harbor. Tow-level start/end GPS tracks ($GPS_{\text{start}}$, $GPS_{\text{end}}$) require FSI scientific logbooks or Vessel Monitoring System (VMS) integration.

### B. Benchmark Leakage Prevention Methodology
In `BenchmarkPartitionValidator`, ORCA enforces two deterministic guards against data leakage:
1. **Duplicate Leakage:** Evaluates SHA256 record signatures across partitions. Any collision between training and evaluation splits raises `duplicate_leakage_detected` and invalidates the benchmark split.
2. **Temporal Leakage:** When evaluating temporal generalizations (`temporal_cutoff`), the validator ensures:
   $$\min(T_{\text{eval}}) > \max(T_{\text{train}})$$
   Any evaluation observation timestamped at or before the training cutoff raises `temporal_leakage_detected`.

### C. Satellite Chlorophyll Freshness Status
- In accordance with the 24-hour chlorophyll freshness policy (`DEFAULT_MAX_AGE['chlorophyll_a'] = timedelta(hours=24)`), fresh usable chlorophyll coverage remains confirmed at **0.0%**.
- Arabian Sea VIIRS passes return 100% null/cloud-masked cells and orbital passes are $>10$ days old. Environmental stations linked to fisheries data correctly flag chlorophyll as unavailable or stale.

### D. Prediction Accuracy Status: Strictly NOT_EVALUABLE
- Precision, Recall, F1, and ROC-AUC scores are **not calculable**.
- Until authorized ground-truth CSV records from CMFRI or FSI are imported and validated, any attempt to evaluate prediction accuracy would constitute unverified speculation. ORCA marks accuracy metrics as `NOT_EVALUABLE` with explanation:
  > *"Zero verified in-situ biological ground-truth labels exist in the operational repository. Predictive accuracy, Precision, Recall, and F1 scores are withheld to preserve scientific integrity."*

---

## 6. Verification & Test Execution Summary

The test suites were executed cleanly:

| Suite | Component Tested | Execution Command | Result |
| :--- | :--- | :--- | :--- |
| **Ground-Truth Import Unit Suite** | Empty files, missing columns, invalid species, duplicate rows, out-of-bounds coordinates, future timestamps, incompatible units, unauthorized quarantine, valid import, dry-run mode, split leakage, and chlorophyll freshness | `pytest tests/unit/test_ground_truth_import_v2_5.py -v` | **14 / 14 passed (0.12s)** |
| **Fisheries Adapter Unit Suite** | Authorized normalization, duplicate detection, taxonomic gates, spatial uncertainty, voyage consistency | `pytest tests/unit/test_fisheries_adapter_v2_4.py -v` | **10 / 10 passed (0.11s)** |
| **Full Backend Suite** | All 277 backend unit, agent, data source, and evaluation tests | `pytest tests/ -q` | **277 passed (0 failures)** |
| **Frontend Integration Suite** | 34 live frontend API service and multi-agent integration tests | `npm test` | **34 / 34 passed (27s)** |
| **Google Chrome Browser Suite** | Headless Chrome browser testing all 6 agents, light theme, SVG map, tabs, and error banners | `npm run test:browser` | **21 / 21 passed** |

---

## 7. Remaining External Blockers & Next Actions

1. **Submit Formal Requisition to ICAR-CMFRI:** Dispatch formal data access request to Director, ICAR-CMFRI, Kochi for West Coast pelagic landing center statistics (2023–2025).
2. **Execute Ingestion via Dry-Run:** Once the CSV export is delivered by CMFRI, run `GroundTruthCsvImporter(is_dry_run=True)` to verify zero schema mismatches and validate CPUE distributions.
3. **Generate Partitioned Benchmark Split:** Use `BenchmarkPartitionValidator` with `split_method="temporal_cutoff"` to create the first ground-truth evaluated benchmark partition in `data/benchmarks/`.
