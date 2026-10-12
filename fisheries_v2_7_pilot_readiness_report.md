# ORCA Fisheries Intelligence v2.7 — Pilot Readiness & Data Acquisition Report

**Document Version:** 2.7.0  
**Pilot Target Area:** Eastern Arabian Sea Corridor / West Coast Indian EEZ (Goa, Malim, Ratnagiri, Mumbai, Karwar, Mangalore)  
**Historical Data Horizon:** 2023–2025 Commercial Landings  
**Operational Biological Store Status:** `AWAITING_AUTHORIZED_DATA`  
**Chlorophyll Fresh Usable Coverage:** **0.0%** (24h Freshness Policy Strictly Preserved)  
**Prediction Evaluation Status:** **NOT_EVALUABLE** (Zero Ground-Truth Labels Ingested)  
**Final Readiness Classification:** `SOFTWARE_DEMO_READY` & `AWAITING_AUTHORIZED_DATA`  

---

## 1. Executive Summary & Readiness Classification

ORCA v2.7 delivers the final pilot readiness verification for the platform. The system is classified under two distinct, evidence-backed readiness states:
1. **`SOFTWARE_DEMO_READY` (VERIFIED):**
   - The application core, the five specialist agents (`WeatherAgent`, `OceanAgent`, `FishingZoneAgent`, `RouteAgent`, `SafetyRiskAgent`), the LangGraph orchestrator, the offline ground-truth import pipeline, and the React frontend dashboard are completely stable, tested, and passing all 287 backend tests, 34 frontend live integration tests, and 21 Google Chrome headless browser checks.
2. **`AWAITING_AUTHORIZED_DATA` (VERIFIED):**
   - The operational biological store contains **0 records**. In accordance with the Zero Data Fabrication Policy, no synthetic fish records or fabricated labels were injected into operational or baseline datasets.
   - The platform will attain `DATA_INGESTION_VALIDATED` only after the official CMFRI dataset is delivered and imported through `GroundTruthCsvImporter(is_dry_run=False)`.
   - The platform will attain `SCIENTIFICALLY_EVALUATED` only after independent ground-truth evaluation is performed on that authorized data.

---

## 2. Official CMFRI Acquisition Package Specification

### A. Pilot Landing Centers (Eastern Arabian Sea Corridor)

| # | Landing Center | District & State | Coordinates | Fleet Categories Monitored |
| :---: | :--- | :--- | :---: | :--- |
| 1 | **Malim Jetty & Panaji** | North Goa, Goa | $15.503^\circ\text{N}, 73.827^\circ\text{E}$ | Mechanized Purse Seine, Motorized Gillnet |
| 2 | **Mirkarwada Harbour** | Ratnagiri, Maharashtra | $16.985^\circ\text{N}, 73.280^\circ\text{E}$ | Mechanized Trawlers, Ring Seine |
| 3 | **Sasoon Docks & Ferry Wharf** | Mumbai, Maharashtra | $18.915^\circ\text{N}, 72.825^\circ\text{E}$ | Multi-day Mechanized Trawlers, Dol Net |
| 4 | **Karwar Baitkhol Harbour** | Uttara Kannada, Karnataka | $14.805^\circ\text{N}, 74.120^\circ\text{E}$ | Rampani Shore Seine, Purse Seine, Trawl |
| 5 | **Old Port / Mangalore Jetty** | Dakshina Kannada, Karnataka | $12.860^\circ\text{N}, 74.835^\circ\text{E}$ | Deep-water Trawl, Oceanic Longline |

### B. Target Taxa & Species Identification Matrix

| Common Name | Binomial Latin Name | FAO Code | Family | Registry Status | Optimal SST Range |
| :--- | :--- | :---: | :--- | :---: | :---: |
| **Indian Mackerel** | *Rastrelliger kanagurta* | `RAK` | Scombridae | **SUPPORTED** | $26.0^\circ\text{C} - 30.0^\circ\text{C}$ |
| **Indian Oil Sardine** | *Sardinella longiceps* | `OIL` | Clupeidae | **SUPPORTED** | $27.0^\circ\text{C} - 30.0^\circ\text{C}$ |
| **Yellowfin Tuna** | *Thunnus albacares* | `YFT` | Scombridae | **SUPPORTED** | $24.0^\circ\text{C} - 29.0^\circ\text{C}$ |
| **Silver Pomfret** | *Pampus argenteus* | `POA` | Stromateidae | **SUPPORTED** | $25.0^\circ\text{C} - 29.5^\circ\text{C}$ |
| **Bombay Duck** | *Harpadon nehereus* | `BOD` | Synodontidae | **SUPPORTED** | $25.0^\circ\text{C} - 29.0^\circ\text{C}$ |

### C. Standardized Schema & Catch/Effort Definitions

```csv
record_identifier,source_agency,dataset_identifier,observation_method,species_name,scientific_name,latitude,longitude,spatial_uncertainty_km,landing_center_name,observed_at,voyage_start_at,voyage_end_at,catch_weight,catch_unit,effort_value,effort_unit,gear_type,is_authorized
```
- **Catch Unit:** Strictly `kg` (kilograms).
- **Effort Unit:** Strictly `hours` (fishing or trawl duration hours).
- **Derived Metric (CPUE):**
  $$\text{CPUE} = \frac{\text{catch\_weight\_kg}}{\text{effort\_hours}} \quad \left(\frac{\text{kg}}{\text{hour}}\right)$$
- **Licensing & Attribution:** Central Marine Fisheries Research Institute (ICAR-CMFRI), Kochi, cited in all published summaries.
- **Privacy & Anonymization:** Vessel names, captain registration numbers, and financial transaction values must be hashed or omitted prior to ingestion.

### D. Outstanding Methodological Inquiries for CMFRI
1. **Engine Horsepower Calibration:** How does CMFRI calibrate effort between multi-day mechanized trawlers (350 HP) vs motorized artisanal canoes (9.9 HP) operating in the same coastal grid?
2. **Zero-Catch Haul Recording:** Are zero-catch exploratory voyages tracked in the FCSC two-stage cluster sampling database?
3. **Mixed-Species Effort Allocation:** When a single haul yields both mackerel and sardines, is effort reported on the aggregate voyage or partitioned per taxon?
4. **Harbor Buffer Geolocation:** What offshore spatial uncertainty radius (15–30 NM) is assigned to harbor landings lacking vessel GPS logbooks?

---

## 3. Operational Evidence Store & Environmental Status

### A. Biological Evidence Store
- **Current Record Count:** **0** records in operational biological storage.
- **Reason:** In accordance with the Zero Data Fabrication Policy, no mock records or simulated labels have been injected. The pipeline remains in state `AWAITING_AUTHORIZED_DATA`.

### B. Remote-Sensing Chlorophyll-a Status
- **NOAA CoastWatch ERDDAP:** Returns HTTP 200 with 100% null/masked grid points over the Arabian Sea bounding box ($14.0^\circ\text{N} - 16.5^\circ\text{N}$, $71.0^\circ\text{E} - 74.5^\circ\text{E}$) due to monsoon/post-monsoon cloud cover. The most recent unmasked satellite overpasses are $>10$ days old.
- **Freshness Policy Enforcement:** Under `DEFAULT_MAX_AGE['chlorophyll_a'] = timedelta(hours=24)`, stale passes are rejected.
- **Usable Fresh Coverage:** **0.0%**. This 0.0% figure is transparently reported in all benchmarks rather than fabricating synthetic ocean-color data.

### C. Scientific Prediction Validation Status
- **Classification Accuracy:** **NOT_EVALUABLE**.
- Precision, Recall, F1, and ROC-AUC scores are withheld until independent, authorized ground-truth labels are acquired from CMFRI and imported through `GroundTruthCsvImporter`.

---

## 4. Next Required Action

- **Dispatch Formal Requisition:** Submit the completed acquisition package to the Director, ICAR-CMFRI, Kochi, to obtain 2023–2025 West Coast landing statistics under the ICAR Data Access Policy.
- Upon file receipt, execute `GroundTruthCsvImporter(is_dry_run=False)` to onboard the records into the evaluated benchmark partition.
