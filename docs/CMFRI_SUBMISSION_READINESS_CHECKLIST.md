# ICAR-CMFRI Fisheries Ground-Truth Requisition: Submission-Readiness Checklist & Final Institutional Audit

**Date / Time:** 2026-10-13 11:35 UTC+5:30  
**Target Repository:** ORCA Marine Intelligence & Advisory Platform (`D:\orca`)  
**Core Requisition Package:** [`CMFRI_DATA_REQUISITION_PACKAGE_v2_8.md`](file:///d:/orca/CMFRI_DATA_REQUISITION_PACKAGE_v2_8.md)  
**Readiness Audit Reference:** [`docs/V2_8_1_ONBOARDING_READINESS_AUDIT.md`](file:///d:/orca/docs/V2_8_1_ONBOARDING_READINESS_AUDIT.md)  
**Software Baseline:** `v2.8.1` (Pre-submission Readiness Frozen Baseline)

---

## 1. Confirmation of Documentation Corrections

The two corrections identified in the v2.8.1 onboarding audit have been verified in [`CMFRI_DATA_REQUISITION_PACKAGE_v2_8.md`](file:///d:/orca/CMFRI_DATA_REQUISITION_PACKAGE_v2_8.md):

| Documentation Item | Updated Package Content (Lines 209–246) | Implementation Reference | Status |
| :--- | :--- | :--- | :---: |
| **Spatial Uncertainty Default** | Line 222: `$\ge 0.0$ (Default: $5.0$, max: $50.0$)` | [`biological_adapter.py:64`](file:///d:/orca/backend/app/data_sources/biological_adapter.py#L64)<br>[`ground_truth_import.py:377`](file:///d:/orca/backend/app/data_sources/ground_truth_import.py#L377) | **CONFIRMED & CONSISTENT** |
| **Schema Header Counts & Gate Enforcement** | Lines 209, 233, 236–246: Explicitly documents **13 mandatory schema headers** validated during CSV parsing (`CANONICAL_REQUIRED_COLUMNS`), plus the 14th column (`access_authorization_token`) enforced at Gate 6 for authorized commitment. | [`ground_truth_import.py:47-61`](file:///d:/orca/backend/app/data_sources/ground_truth_import.py#L47-L61)<br>[`biological_adapter.py:205-224`](file:///d:/orca/backend/app/data_sources/biological_adapter.py#L205-L224) | **CONFIRMED & CONSISTENT** |

---

## 2. Complete Inventory of Remaining Placeholders

Before transmission to ICAR-CMFRI, the Principal Investigator must replace the following placeholders in [`CMFRI_DATA_REQUISITION_PACKAGE_v2_8.md`](file:///d:/orca/CMFRI_DATA_REQUISITION_PACKAGE_v2_8.md):

| Line Number | Section | Placeholder Text | Action Required by PI |
| :---: | :--- | :--- | :--- |
| **Line 142** | Part B (Draft Letter Sign-off) | `[TO BE FILLED BY PI — Project Principal Investigator Name]` | Insert full legal name of Principal Investigator |
| **Line 143** | Part B (Draft Letter Sign-off) | `[TO BE FILLED BY PI — Designation & Institutional Affiliation]` | Insert official academic/research designation and department |
| **Line 144** | Part B (Draft Letter Sign-off) | `[TO BE FILLED BY PI — Institutional Postal Address]` | Insert official university/institutional postal address |
| **Line 145** | Part B (Draft Letter Sign-off) | `[TO BE FILLED BY PI — Official Institutional Email Address]` | Insert institutional `.edu` / `.ac.in` / `.res.in` email address |
| **Line 145** | Part B (Draft Letter Sign-off) | `[TO BE FILLED BY PI — Telephone / Mobile]` | Insert official landline and mobile contact numbers |
| **Line 147** | Part B (Draft Letter Sign-off) | `[TO BE FILLED BY PI — Date of dispatch on letterhead]` | Insert actual dispatch date when printed on letterhead |
| **Line 275** | Part D (Contact Table) | `[TO BE FILLED BY PI — Principal Investigator]` | Insert PI name in the contact table |
| **Line 275** | Part D (Contact Table) | `[TO BE FILLED BY PI — Institutional email]` | Insert PI institutional email address |
| **Line 276** | Part D (Contact Table) | `[TO BE FILLED BY PI — Systems Architecture Lead]` | Insert Technical Data Custodian / Systems Lead name |
| **Line 276** | Part D (Contact Table) | `[TO BE FILLED BY PI — Institutional email]` | Insert Technical Data Custodian email address |

---

## 3. Pending Confirmations & Operational Issues

The following technical and institutional questions are explicitly logged as pending external resolution:

### A. Species Coding Discrepancies (Blockers B-4 & B-5)
1. **Indian Mackerel (*Rastrelliger kanagurta*):**
   * *Status:* Canonical FAO ASFIS code is **`RAG`**; older CMFRI and INCOIS PFZ bulletins frequently use **`RAK`**.
   * *Software Behavior:* ORCA's registry resolves both `RAG` and `RAK` to Indian Mackerel.
   * *Pending Confirmation:* ICAR-CMFRI must confirm which 3-alpha code is exported in their official NMFDC datasets.
2. **Silver Pomfret (*Pampus argenteus*):**
   * *Status:* Canonical FAO ASFIS code is **`SIP`**; historical ICAR and regional cataloging often cite **`POA`**.
   * *Software Behavior:* ORCA's registry resolves both `SIP` and `POA` to Silver Pomfret.
   * *Pending Confirmation:* ICAR-CMFRI must confirm whether `SIP` or `POA` appears in their data exports.
3. **Tuna Separation:**
   * Yellowfin Tuna (**`YFT`**) and Skipjack Tuna (**`SKJ`**) are maintained as separate species in ORCA. CMFRI must provide separate line items for each species.

### B. Authorization Token Procedure (Blocker B-6)
* *Status:* Required by software ingestion gate (Gate 6). In-band `is_authorized=true` declarations cannot authorize ingestion.
* *Pending Confirmation:* CMFRI/PI must confirm the out-of-band delivery mechanism, validity period, and batch scope of the `access_authorization_token`.

### C. Data-Sharing Agreement & MoU (Blocker B-3)
* *Status:* No bilateral agreement has been executed.
* *Pending Confirmation:* Institutional administration must establish the formal legal agreement or MoU governing non-commercial research use.

### D. Temporal Granularity (Blocker B-7)
* *Status:* ORCA's CPUE calculation requires active fishing duration in **hours** ($\text{CPUE} = \text{catch\_kg} / \text{effort\_hours}$). Units of `days` are rejected.
* *Pending Confirmation:* CMFRI must confirm whether 2023–2025 records are available as individual landing hauls with active hours, or only as monthly aggregates with days fished.

### E. Spatial Coordinate Semantics (Blocker B-8)
* *Status:* Spatial uncertainty is bounded at $\le 50.0\text{ km}$. Harbor landing sites are stored in `metadata["landing_center"]`.
* *Pending Confirmation:* CMFRI must confirm whether exported coordinates represent the landing harbor jetty or the offshore catch ground centroid.

---

## 4. Document Checklist & Status Separation

| Document / Asset | Scope | Status | Next Required Step |
| :--- | :--- | :---: | :--- |
| **`CMFRI_DATA_REQUISITION_PACKAGE_v2_8.md`** | Institutional Requisition Package | **READY FOR REVIEW** | PI reviews, fills placeholders, and signs |
| **`docs/V2_8_1_ONBOARDING_READINESS_AUDIT.md`** | Pre-submission Technical Audit | **READY FOR REVIEW** | Retained as technical annexure |
| **`docs/CMFRI_SUBMISSION_READINESS_CHECKLIST.md`** | Submission-Readiness Checklist | **READY FOR REVIEW** | Guide for PI submission workflow |
| **Official Letterhead Request** | Institutional Endorsement | **NOT YET OBTAINED** | Print on university letterhead with PI signature |
| **CMFRI Data-Sharing Agreement / MoU** | Legal Bilateral Agreement | **NOT INITIATED** | University administration initiates with CMFRI |
| **Out-of-Band Authorization Token** | Custodian Access Credential | **NOT YET OBTAINED** | CMFRI issues upon approval |
| **Authorized Ground-Truth Dataset (CSV)** | Empirical Fisheries Data | **AWAITING DATA** | Pending formal release by CMFRI |

---

## 5. Formal Questions for ICAR-CMFRI

The following questions should accompany the formal requisition letter:

1. **Authorization & Token Delivery:**  
   *What is the institutional protocol for issuing the out-of-band authorization token for batch verification? What validity period and revocation terms apply?*
2. **Species Coding Standards:**  
   *Does CMFRI's NMFDC database use current FAO ASFIS codes (`RAG` for Indian Mackerel, `SIP` for Silver Pomfret) or historical project notations (`RAK`, `POA`)?*
3. **Temporal Granularity & Effort Reporting:**  
   *Are commercial landing records for 2023–2025 available at individual voyage/trip resolution with active fishing hours, or only as monthly harbor aggregates? If aggregated, does CMFRI provide standardized fleet conversion factors to estimate effective fishing hours?*
4. **Spatial Reference Convention:**  
   *Do the latitude and longitude fields in the export indicate the landing jetty, the estimated offshore fishing ground centroid, or an ICAR statistical survey grid?*
5. **Administrative Form & Fee Schedule:**  
   *Is there a prescribed NMFDC requisition proforma, data-sharing agreement template, or administrative processing fee required for non-commercial academic research?*

---

## 6. Software Baseline & Scientific Invariant Summary

* **Backend Test Suite:** 305 tests passing (`pytest -q`, exit code 0).
* **Frontend Test Suite:** 34 tests passing (17 unit + 17 integration, exit code 0).
* **Biological Operational Store:** Strictly preserved as `AWAITING_AUTHORIZED_DATA` (zero synthetic or unverified observations in storage).
* **Predictive Accuracy:** Withheld and preserved as `NOT_EVALUABLE`.
* **Freshness Guarantees:** 24-hour satellite chlorophyll-a freshness policy enforced.

---

## 7. Final Submission-Readiness Status

# **`READY_FOR_PI_REVIEW`**

### Supporting Findings:
1. **Zero Missing Internal Documents:** All required requisition documentation, technical annexures, schema specifications, and audit reports are fully drafted, hardened, and verified in the repository.
2. **Documentation Inconsistencies Resolved:** Spatial uncertainty default ($5.0\text{ km}$) and header validation counts (13 schema + 1 gate-enforced) are completely aligned with the implementation.
3. **Software Freeze Maintained:** The codebase is locked, stable, and verified with 100% pass rates across test suites.
4. **Administrative Responsibility Isolated:** The remaining steps belong exclusively to the Principal Investigator (populating contact fields, signing on official letterhead, and initiating institutional contact with ICAR-CMFRI).
