# ORCA Marine Intelligence & Fishing Advisory Platform
## v3.4 Data Acquisition Readiness & Submission Preparation Action Plan

**Document Version:** 3.4.0  
**Date of Plan:** 2026-10-13  
**Target Repository:** `D:\orca`  
**Operational Biological Store Status:** `AWAITING_AUTHORIZED_DATA`  
**Requisition Package Status:** `DRAFT — PENDING MANUAL PI SIGNATURE & DISPATCH`  
**External Submission Status:** `UNSUBMITTED — NO FORMS TRANSMITTED, NO EMAILS SENT`  
**Biological Model Status:** `NO_TRAINED_MODEL — PREDICTIONS STRICTLY WITHHELD`  
**Onboarding Test Suite Status:** `65/65 TESTS PASSING (100%)`  

---

## 1. Executive Context & Biological Safeguards

This action plan defines the operational roadmap for submitting the external fisheries data requisition to the **ICAR - Central Marine Fisheries Research Institute (CMFRI)** and executing the post-receipt ingestion sequence once authentic biological ground-truth records are released.

### Non-Negotiable Safeguards & Scientific Invariants:
1. **Unsubmitted Draft Integrity:** The formal requisition package ([`CMFRI_DATA_REQUISITION_PACKAGE_v2_8.md`](file:///D:/orca/CMFRI_DATA_REQUISITION_PACKAGE_v2_8.md)) remains an unsubmitted draft. No automated communications, web requests, emails, or form submissions have been conducted or simulated.
2. **Strict Prediction Withholding:** In the absence of validated institutional observations:
   - `operational_store = "AWAITING_AUTHORIZED_DATA"`
   - `fish_presence = "UNVERIFIED"`
   - `catch_probability = None`
   - `biomass_prediction = None`
   - `predictive_accuracy = "NOT_EVALUABLE"`
3. **No Synthetic Credentials or Data:** Out-of-band authorization tokens (`access_authorization_token`) cannot be fabricated, hardcoded, or bypassed. In-band declarations (`is_authorized=true`) will not authorize ingestion without an authentic external token.
4. **Scope Boundaries:** This document is strictly documentation-only. No application code, data schemas, or authorization gates are modified.

---

## 2. Separation of Responsibilities & Readiness Classification

To prevent ambiguity, project responsibilities are strictly separated between software engineering readiness, institutional leadership, legal administration, and external custodian actions:

```mermaid
graph TD
    subgraph Track 1: Software Readiness [Track 1: Software Systems & Importer (ORCA Engineering - 100% Complete)]
        S1[13-Column Canonical Parser]
        S2[Dual Species Code Registry]
        S3[6 Quality Gates & Token Check]
        S4[Dry-Run Quarantine Pipeline]
        S5[65/65 Unit Test Baseline]
    end

    subgraph Track 2: PI Leadership [Track 2: Principal Investigator (PI Action Required - Pending)]
        P1[Fill Contact Placeholders]
        P2[Transfer to Official Letterhead]
        P3[Manual Signature & Stamp]
        P4[Transmit Technical Queries]
        P5[Log Dispatch Reference]
    end

    subgraph Track 3: Legal Admin [Track 3: University Administration (Legal Action Required - Pending)]
        L1[Initiate Data-Sharing Agreement]
        L2[Execute Bilateral MoU with CMFRI]
        L3[Affirm Non-Commercial Academic Terms]
    end

    subgraph Track 4: CMFRI Custodian [Track 4: ICAR-CMFRI Custodian (External Action Required - Pending)]
        C1[Review & Approve Requisition]
        C2[Issue Out-of-Band Auth Token]
        C3[Confirm Species Coding & Units]
        C4[Clarify Effort & Coordinates]
        C5[Release 2023-2025 Dataset]
    end

    Track 2 --> Track 3
    Track 3 --> Track 4
    Track 4 --> Track 1
```

### Readiness Summary:
* **Track 1 (Software Systems):** **100% READY & FROZEN.** Parser, schema mappings, 6-gate validation pipeline, dry-run quarantine, and zero-mutation safeguards are verified by 65 passing tests.
* **Track 2 (Principal Investigator):** **PENDING PI REVIEW & SIGNATURE.** Awaiting physical populating of contact details and signature on university letterhead.
* **Track 3 (University Administration):** **PENDING LEGAL INITIATION.** Awaiting formal bilateral MoU / Data-Sharing Agreement initiation with CMFRI Kochi.
* **Track 4 (ICAR-CMFRI Custodians):** **AWAITING SUBMISSION.** No contact has been initiated; pending receipt of signed package.

---

## 3. Comprehensive Action Table

The following table details every outstanding blocker, specifying the responsible party, required verification evidence, technical dependency, and current completion status:

| Blocker ID | Domain | Action / Requirement | Responsible Party | Dependency | Required Verification Evidence | Completion Status |
| :---: | :--- | :--- | :--- | :--- | :--- | :---: |
| **B-1** | **PI Contact Details** | Replace 8 placeholder tags (`[TO BE FILLED BY PI]`) in Lines 142–147 and 275–276 of `CMFRI_DATA_REQUISITION_PACKAGE_v2_8.md`. | Principal Investigator | None | Full legal name, academic title, university address, official institutional `.edu`/`.ac.in`/`.res.in` email, and direct phone number inserted. | `PENDING_PI_ACTION` |
| **B-2** | **Institutional Signature** | Print formal request on university letterhead; apply manual signature, date, and departmental seal. | PI & Department Head | **B-1** | Physical or certified PDF document bearing university letterhead, signature, institutional seal, and dispatch tracking number. | `PENDING_PI_SIGNATURE` |
| **B-3** | **Data-Sharing Agreement / MoU** | Draft and execute bilateral academic data-sharing agreement governing non-commercial research use. | University Legal Cell & CMFRI Administration | **B-2** | Fully executed bilateral MoU / Data-Sharing Agreement signed by authorized institutional signatories of both entities. | `PENDING_LEGAL_INITIATION` |
| **B-4** | **Species Code: Mackerel** | Obtain written confirmation whether CMFRI exports use canonical FAO code `RAG` or historical CMFRI code `RAK` (*Rastrelliger kanagurta*). | ICAR-CMFRI Custodian (FRAEED / NMFDC) | Requisition Package Transmission (§5.2) | Official CMFRI response, data dictionary, or schema specification confirming the 3-alpha code. *(Software is dual-ready).* | `AWAITING_EXTERNAL_CONFIRMATION` |
| **B-5** | **Species Code: Pomfret & Tuna** | Confirm whether Silver Pomfret uses `SIP` or `POA` (*Pampus argenteus*), and verify Yellowfin (`YFT`) and Skipjack (`SKJ`) Tuna are separate lines. | ICAR-CMFRI Custodian (FRAEED / NMFDC) | Requisition Package Transmission (§5.2) | Written confirmation of Pomfret code and verification of separate Tuna rows. *(Software is dual-ready).* | `AWAITING_EXTERNAL_CONFIRMATION` |
| **B-6** | **Authorization Token Protocol** | Establish out-of-band delivery mechanism, batch validity duration, and revocation procedure for Gate 6 ingestion token. | CMFRI Data Custodian & ORCA Technical Lead | **B-3** | Documented out-of-band token transmission protocol; issuance of authentic batch token with defined expiry. *(Gate 6 is active).* | `AWAITING_PROTOCOL_DEFINITION` |
| **B-7** | **Sampling Effort Resolution** | Confirm whether commercial landing records supply trip-level active fishing duration in hours, or monthly harbor days requiring fleet conversion factors. | ICAR-CMFRI FRAEED Division | Requisition Package Transmission (§5.3) | Methodological documentation specifying effort units or CMFRI-certified gear-specific multipliers. *(Hours enforced, days rejected).* | `AWAITING_METHODOLOGY_CONFIRMATION` |
| **B-8** | **Spatial Coordinate Semantics** | Confirm whether coordinates represent harbor landing jetty or offshore fishing ground polygon centroid. | ICAR-CMFRI FRAEED Division | Requisition Package Transmission (§5.4) | Technical memorandum detailing spatial reference conventions. *(Spatial uncertainty $\le 50.0\text{ km}$ enforced).* | `AWAITING_GEOGRAPHIC_CONFIRMATION` |

---

## 4. Final Pre-Submission Checklist

Before the Principal Investigator and University Administration transmit the requisition package to ICAR-CMFRI, every checklist item below must be systematically verified and signed off:

### 4.1 Contact & Institutional Details
- [ ] **1. PI Name & Designation:** Full legal name and academic title inserted (no placeholders remaining).
- [ ] **2. Institutional Affiliation & Address:** Department name, university/institute, and postal address confirmed.
- [ ] **3. Official Email & Telephone:** Institutional domain email (`.ac.in` / `.edu` / `.res.in`) and direct telephone entered.
- [ ] **4. Technical Custodian Details:** ORCA Systems Architecture Lead contact information verified in Part D table.

### 4.2 Letterhead, Signature & Administrative Approval
- [ ] **5. Official Letterhead:** Requisition text transferred to official university / institute stationery.
- [ ] **6. Institutional Dispatch Number:** Formal outgoing dispatch/reference number generated and printed on document.
- [ ] **7. Manual PI Signature & Date:** Handwritten or authenticated digital signature applied by the Principal Investigator.
- [ ] **8. Departmental / Dean Seal:** Official institutional rubber stamp or digital certificate affixed.

### 4.3 Legal & Data Governance (MoU / Data-Sharing Agreement)
- [ ] **9. Non-Commercial Academic Undertaking:** Explicit commitment affirming data will be used solely for open public-good research.
- [ ] **10. Anonymization Commitment:** Undertaking to scrub Vessel Registration Numbers (VRNs), crew names, and proprietary commercial identifiers.
- [ ] **11. MoU Terms Drafted:** Standard institutional data-sharing agreement draft prepared for CMFRI Legal Cell review.

### 4.4 Technical Specification Inquiries Included
- [ ] **12. Species Code Confirmation Appended:** Formal inquiry regarding `RAG` vs `RAK` and `SIP` vs `POA` included in transmission.
- [ ] **13. Effort Resolution Query Included:** Formal inquiry regarding active fishing hours vs days/voyages and aggregate multipliers included.
- [ ] **14. Coordinate Semantics Query Included:** Formal inquiry regarding landing jetty vs catch centroid reference system included.
- [ ] **15. Token Protocol Query Included:** Request for out-of-band delivery instructions, expiry, and revocation terms included.

### 4.5 Dataset Format & Canonical 13-Column Schema Attached
- [ ] **16. CSV File Format Specification Attached:** UTF-8 encoding (with/without BOM), comma-delimited, CRLF/LF line terminations specified.
- [ ] **17. Technical Annexure Attached:** Technical Annexure specifying the **13 canonical CSV headers** and required data types attached to requisition:

| Column # | Canonical Column Header | Required Type | Permissible Range / Format | Mandatory Validation Gate |
| :---: | :--- | :---: | :--- | :--- |
| **1** | `record_id` | String | Unique alphanumeric identifier | Primary key / deduplication |
| **2** | `agency` | String | Non-empty (`CMFRI`, `NMFDC`, `FSI`) | Provenance verification |
| **3** | `species_code` | String | 3-alpha canonical code (`RAG`, `SIP`, `IOS`, `YFT`, `SKJ`) | Gate 1 (Species Resolution) |
| **4** | `scientific_name` | String | Taxonomic binomial name | Cross-validation with species code |
| **5** | `timestamp_utc` | String | ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ`) | Gate 3 (Temporal / Non-future) |
| **6** | `latitude` | Float | $[-90.0, 90.0]$ | Gate 2 (Spatial Bounding) |
| **7** | `longitude` | Float | $[-180.0, 180.0]$ | Gate 2 (Spatial Bounding) |
| **8** | `spatial_uncertainty_km` | Float | $\ge 0.0$ (Default: $5.0$, Maximum: $50.0$) | Gate 2 (Spatial Precision) |
| **9** | `catch_kg` | Float | $\ge 0.0$ | Gate 4 (Effort / Catch Bounds) |
| **10** | `effort_hours` | Float | $> 0.0$ (Active duration in hours) | Gate 4 (Effort / Catch Bounds) |
| **11** | `cpue_kg_per_hour` | Float | $\ge 0.0$ ($\text{catch\_kg} / \text{effort\_hours}$) | Gate 4 (Mathematical Consistency) |
| **12** | `gear_type` | String | Standard gear classification | Descriptive metadata |
| **13** | `observation_method` | String | `COMMERCIAL_LANDING_STATISTIC` | Gate 5 (Method Categorization) |
| *Auth* | `access_authorization_token` | Secret | Non-empty alphanumeric credential supplied out-of-band | **Gate 6 (Authorization Verification)** |

---

## 5. Post-Receipt Ingestion Procedure

When ICAR-CMFRI formally releases the dataset, the ORCA Technical Custodian must execute the following strict 6-step procedure:

```
[Incoming CMFRI Dataset]
           │
           ▼
[Step 1: Provenance & Authorization Verification] ──► Fails? ──► [Reject Batch / Alert Custodian]
           │
           ▼
[Step 2: File Integrity & Checksum Verification] ──► Fails? ──► [Quarantine Corrupt File]
           │
           ▼
[Step 3: Execute Dry-Run Importer] ───────────────► Fails? ──► [Quarantine & Audit Divergences]
           │
           ▼
[Step 4: Review Quarantined Records & Errors] ────► Divergences > 0? ──► [Halt & Investigate]
           │
           ▼
[Step 5: Live Ingestion & 6-Gate Enforcement] ────► Invalid Records? ──► [Drop / Isolate Invalid]
           │
           ▼
[Step 6: Atomic Commit to Operational Store] ─────► Transition Store to AUTHORIZED_DATA_ONBOARDED
```

### Step 1: Verify Provenance & Authorization
1. Verify the transmitting source matches official ICAR-CMFRI email domains (`director.cmfri@icar.gov.in`, `fraeed.cmfri@icar.gov.in`, or designated portal).
2. Confirm the formal dataset transmission memo / release letter referencing the executed Data-Sharing Agreement.
3. Obtain the out-of-band `access_authorization_token` via secure institutional delivery. Verify it is non-empty, contains no whitespace-only characters, and matches the authorized dataset batch scope.

### Step 2: File Integrity & Checksum Verification
1. Calculate the SHA-256 cryptographic hash of the received CSV immediately upon download:
   ```powershell
   Get-FileHash -Path "path\to\cmfri_landing_data_2023_2025.csv" -Algorithm SHA256
   ```
2. Log the file name, size, byte count, and SHA-256 hash in the institutional data provenance register.
3. Confirm encoding is UTF-8 (or UTF-8 with BOM) and line endings are valid CRLF or LF.

### Step 3: Execute Existing Dry-Run Importer
1. Invoke `OfflineGroundTruthImporter.parse_csv_stream` with `is_dry_run=True`:
   ```python
   importer = OfflineGroundTruthImporter(biological_adapter)
   dry_run_summary = importer.parse_csv_stream(
       csv_text_stream=dataset_content,
       file_name="cmfri_landing_data_2023_2025.csv",
       file_checksum=file_sha256_hash,
       is_dry_run=True,
       access_authorization_token=out_of_band_token
   )
   ```
2. Assert that `len(biological_adapter._normalized_records)` remains completely unchanged before and after the dry-run invocation.

### Step 4: Review Rejected / Quarantined Records
1. Inspect the `dry_run_summary` metrics:
   - `total_rows_parsed`: Total rows processed from stream.
   - `valid_rows_identified`: Rows passing all 6 validation gates.
   - `quarantined_rows`: Total rows flagged with errors.
   - `quarantine_reasons`: Detailed counter of error categories (e.g. `UNSUPPORTED_SPECIES`, `INVALID_COORDINATES`, `FUTURE_DATE`, `ZERO_EFFORT`, `UNAUTHORIZED_RECORD`).
2. If `quarantined_rows > 0`, conduct an audit of flagged records against CMFRI's data dictionary. If fundamental schema divergences exist, halt ingestion and notify the CMFRI Data Custodian.

### Step 5: Live Ingestion & Six-Gate Enforcement
1. When the dry run produces 100% compliant rows or an approved quarantined tolerance, execute live ingestion with `is_dry_run=False`:
   ```python
   live_summary = importer.parse_csv_stream(
       csv_text_stream=dataset_content,
       file_name="cmfri_landing_data_2023_2025.csv",
       file_checksum=file_sha256_hash,
       is_dry_run=False,
       access_authorization_token=out_of_band_token
   )
   ```
2. The importer enforces the 6 quality gates sequentially:
   - **Gate 1 (Taxonomy):** Species resolves against ORCA canonical registry (`species_rules.py`).
   - **Gate 2 (Spatial):** Latitude $\in [-90, 90]$, Longitude $\in [-180, 180]$, spatial uncertainty $\le 50.0\text{ km}$.
   - **Gate 3 (Temporal):** Valid ISO 8601 UTC timestamp; non-future date check.
   - **Gate 4 (Effort/Catch):** Catch $\ge 0.0\text{ kg}$, effort $> 0.0\text{ hours}$, CPUE $\ge 0.0\text{ kg/hour}$.
   - **Gate 5 (Observation Method):** Must match `COMMERCIAL_LANDING_STATISTIC`.
   - **Gate 6 (Authorization):** In-band `is_authorized=True` corroborated by valid out-of-band token.

### Step 6: Atomic Commit & Audit Sign-Off
1. Commit only valid, authorized records into the biological adapter.
2. Confirm that `file_sha256_hash` is recorded in `imported_file_checksums` to prevent duplicate re-ingestion.
3. Formally transition operational biological store status from `AWAITING_AUTHORIZED_DATA` to `AUTHORIZED_DATA_ONBOARDED`.
4. Construct rigorous temporal evaluation partitions (train/test) without cross-partition temporal leakage for subsequent benchmark evaluation.

---

## 6. Biological Telemetry & Safeguard Summary

The current system state and operational responses are confirmed as follows:

| System Subsystem | Operational State | Runtime Behavior & Invariant |
| :--- | :---: | :--- |
| **Operational Biological Store** | **`AWAITING_AUTHORIZED_DATA`** | Zero records stored; rejected and unverified data are never committed. |
| **Fish Presence Telemetry** | **`UNVERIFIED`** | All agent responses explicitly report biological presence as unverified. |
| **Catch Probability Advisory** | **`null`** | No numerical probabilities are generated without trained models. |
| **Pelagic Biomass Prediction** | **`None`** | Direct biomass predictions are strictly withheld. |
| **Benchmark Predictive Accuracy** | **`NOT_EVALUABLE`** | Precision, recall, and F1 scores remain unavailable. |
| **Environmental Vessel Safety** | **`HEURISTIC_ONLY`** | Physical wave and weather safety are evaluated strictly as vessel operability. |
| **Institutional Request Status** | **`DRAFT_PENDING_PI`** | Formal requisition drafted, audited, and awaiting human PI action. |

---

## 7. Verification Baseline

The technical foundation for this data acquisition procedure was re-verified against the complete onboarding and fisheries test suite:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_fisheries_hardening_v2_8.py tests/unit/test_ground_truth_import_v2_5.py tests/unit/test_ground_truth_import_authorization_mix.py tests/unit/test_fisheries_ingestion.py tests/unit/test_fisheries_adapter_v2_4.py -v
```

**Results:** **65 passed in 0.25s (100% pass rate, 0 failures)**
- Self-declared auth bypass rejection: Verified
- UTF-8 BOM handling: Verified
- Coordinate & spatial uncertainty bounds: Verified
- Effort in hours enforcement (days rejection): Verified
- Six quality gates & dry-run quarantine pipeline: Verified
- Out-of-band token whitespace rejection: Verified
