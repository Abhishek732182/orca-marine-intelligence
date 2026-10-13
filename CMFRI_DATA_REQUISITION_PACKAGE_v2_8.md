# ICAR-CMFRI Fisheries Ground-Truth Data Requisition Package

**Document Version:** 2.8.1  
**Project:** ORCA Marine Intelligence & Advisory Platform  
**Target Temporal Period:** January 1, 2023 – December 31, 2025  
**Pilot Geographic Area:** Eastern Arabian Sea / West Coast Indian EEZ  
**Submission Status:** `DRAFT — REQUIRES PI REVIEW AND SIGNATURE BEFORE TRANSMISSION`  
**Operational Biological Store Status:** `AWAITING_AUTHORIZED_DATA`  

> [!IMPORTANT]
> **This is a prepared draft only. Nothing in this document has been transmitted, submitted, or
> signed. All fields marked `[TO BE FILLED BY PI]` MUST be completed by the Principal Investigator
> before this package is printed on institutional letterhead and dispatched. Do not transmit
> this draft electronically to CMFRI without explicit PI authorization.**

---

## Part A: Official Submission Checklist

Before transmitting this data requisition package to the Director, ICAR-CMFRI, ensure that all
institutional and technical items are resolved. Items marked `PENDING` require human action before
submission; items marked `CONFIRMED` are verifiable from project documentation.

| # | Item | Status | Verification & Notes |
| :-: | :--- | :---: | :--- |
| **1** | **Institutional Endorsement** | `PENDING_PI_SIGNATURE` | Cover letter must be printed on institutional letterhead and signed by the Principal Investigator. PI name, designation, and affiliation are placeholders — see Part B. |
| **2** | **Pilot Centers Identified** | `CONFIRMED` | Exactly five strategic landing centers specified (Malim/Panaji, Mirkarwada, Sasoon Docks, Baithkol/Karwar, Mangalore). Coordinates verified against public CMFRI harbor records. |
| **3** | **Target Species & Codes Defined** | `PENDING_CMFRI_CODE_CONFIRMATION` | Five priority species documented with scientific names and proposed FAO 3-alpha codes. Two code discrepancies require CMFRI clarification: Indian Mackerel (`RAG` vs historical `RAK`) and Silver Pomfret (`SIP` vs historical `POA`). See §3 of Technical Annexure and the Species-Code Reconciliation Notice below. |
| **4** | **Temporal Resolution Specified** | `CONFIRMED` | 2023–2025 calendar years requested. Trip-level records preferred; monthly aggregates acceptable if trip-level data is restricted by CMFRI data-privacy policy. |
| **5** | **Required Schema & Units Defined** | `CONFIRMED` | Standard CSV ingestion schema documented with mandatory kg (catch) and hours (effort). See §3 of Technical Annexure. |
| **6** | **Effort & CPUE Definitions Clear** | `CONFIRMED` | CPUE defined as kg/hour. Aggregate monthly records cannot yield individual-voyage CPUE without CMFRI-documented conversion multipliers; this limitation is acknowledged in the schema specification. |
| **7** | **Methodological Inquiries Formulated** | `CONFIRMED` | Outstanding questions on gear standardization, zero-catch trips, multi-species attribution, and preferred taxonomic coding schema formally included in the formal letter (§5). |
| **8** | **Licensing & Attribution Undertaking** | `PENDING_INSTITUTIONAL_MOU` | Research-only evaluation scope and CMFRI citation guidelines are proposed. However, no licensing agreement or MOU has been concluded. The PI must confirm the applicable institutional data-sharing agreement with CMFRI before transmission. |
| **9** | **Data Anonymization Agreement** | `PENDING_PI_SIGNATURE` | Commitment to anonymize VRNs and skipper identities is stated in the letter body; this becomes binding only upon PI signature. |
| **10** | **Recipient Contact Details** | `CONFIRMED` | Director ICAR-CMFRI, Kochi and FRAEED division contacts documented from publicly available CMFRI institutional information. |

---

## Part B: Formal Letter / Email Requisition Draft

> [!WARNING]
> The following is a **DRAFT ONLY**. The PI fields (`[TO BE FILLED BY PI]`) MUST be replaced with
> verified institutional details before printing and dispatch. Do NOT send this draft electronically.

```text
To:
The Director,
ICAR - Central Marine Fisheries Research Institute (CMFRI),
Post Box No. 1603, Ernakulam North P.O.,
Kochi - 682 018, Kerala, India.
Email: director.cmfri@icar.gov.in

Cc:
The Head of Division,
Fishery Resources Assessment, Economics & Extension Division (FRAEED),
ICAR-CMFRI, Kochi - 682 018.
Email: fraeed.cmfri@icar.gov.in

Subject: Official Requisition for Commercial Marine Fisheries Landing Statistics (2023–2025)
         for West Coast Pilot Decision-Support Research (Project ORCA)

Respected Sir / Madam,

Greetings from the ORCA Marine Intelligence & Advisory Platform research team.

We are developing an evidence-grounded marine situational awareness and decision-support system
designed to support artisanal and mechanized fishers along India's Exclusive Economic Zone (EEZ).
The platform integrates physical oceanographic models (sea surface temperature, wave height,
swell dynamics) with official maritime safety advisories to provide situational guidance while
strictly maintaining vessel safety and scientific integrity.

To establish an auditable, scientifically sound ground-truth baseline for our West Coast pilot
evaluation, we formally request authorized commercial fisheries landing statistics collected
under the National Marine Fisheries Data Centre (NMFDC) framework for the calendar years 2023,
2024, and 2025.

1. GEOGRAPHIC SCOPE (FIVE PILOT LANDING CENTERS):
   a) Malim Jetty / Panaji, Goa (15.5036° N, 73.8286° E)
   b) Mirkarwada / Ratnagiri, Maharashtra (16.9902° N, 73.2847° E)
   c) Sasoon Docks / New Ferry Wharf, Mumbai, Maharashtra (18.9167° N, 72.8250° E)
   d) Baithkol / Karwar, Karnataka (14.8055° N, 74.1244° E)
   e) Mangalore Old Port, Karnataka (12.8580° N, 74.8360° E)

2. TARGET COMMERCIAL SPECIES:
   We specifically request catch and effort statistics for the following five commercial species.
   Note: Two species codes are under clarification (see §5 below); we request CMFRI to confirm
   their preferred coding convention in the formal data-sharing agreement.
   - Indian Mackerel (Rastrelliger kanagurta) [proposed: RAG / historical usage: RAK]
   - Indian Oil Sardine (Sardinella longiceps) [FAO: IOS]
   - Yellowfin Tuna (Thunnus albacares) [FAO: YFT] — requested as a SEPARATE line item from Skipjack
   - Skipjack Tuna (Katsuwonus pelamis) [FAO: SKJ] — requested as a SEPARATE line item from Yellowfin
   - Silver Pomfret (Pampus argenteus) [proposed: SIP / historical usage: POA]
   (Optional demersal baseline for Mumbai/Ratnagiri only: Bombay Duck [Harpadon nehereus, FAO: DUC])

3. REQUESTED DATA ATTRIBUTES & FORMAT:
   - Temporal granularity: Trip-level records preferred. Monthly landing aggregations are
     acceptable if trip-level data is restricted under CMFRI data-privacy guidelines.
     NOTE: Monthly aggregate records cannot be used to derive individual-voyage CPUE
     (kg/hour) without CMFRI-documented conversion multipliers.
   - Effort metrics: Actual cumulative fishing duration in active fishing hours preferred.
     Voyage duration in days is acceptable if accompanied by CMFRI's standardized conversion
     factor from voyage-days to estimated effective fishing hours for each gear type.
   - Catch metrics: Landed weight in kilograms (kg). Metric tonnes are acceptable; please
     indicate unit explicitly in the data header or accompanying documentation.
   - Spatial indicators: Landing-center name and coordinates are the primary location reference
     for landed catch. Approximate fishing-ground sector, depth contour (m), or distance
     offshore (km) are requested where available, with an explicit note on whether coordinates
     represent the landing center or the fishing ground.
   - Data format: Standard CSV or structured tabular electronic export with a data dictionary
     defining all column names, units, and coding conventions used.

4. INTENDED USE, PRIVACY & LICENSING:
   - The requested dataset will be used solely for academic validation, benchmark integrity
     testing, and non-commercial research under an institutional evaluation license.
   - All individual vessel names, vessel registration numbers (VRN), and fisher identities will
     remain strictly confidential and anonymized in all outputs and publications.
   - Proper scientific attribution and credit will be prominently cited in all publications and
     technical reports as: "Data source: ICAR-Central Marine Fisheries Research Institute (CMFRI),
     National Marine Fisheries Data Centre (NMFDC), Kochi, India."
   - We request CMFRI's guidance on the applicable data-sharing agreement, administrative
     procedure, and any fees applicable to this release.

5. METHODOLOGICAL QUESTIONS FOR CLARIFICATION:
   We also seek CMFRI's scientific guidance on the following questions:
   a) CMFRI's preferred 3-alpha species code for Rastrelliger kanagurta (RAG or RAK) and
      Pampus argenteus (SIP or POA) in your landing statistics exports.
   b) Recommended gear-effort standardization factor between multi-day trawls and single-day
      purse seines, for converting voyage-days to estimated fishing hours where only voyage
      duration is recorded.
   c) Recording protocol for zero-catch exploratory trips within the landing database
      (whether such trips are omitted, or recorded with catch_weight = 0).
   d) Standard convention for attributing multi-species trawl hauls to unit effort when
      more than one species is landed per trip.

We would be grateful if you could advise us on the formal requisition procedure, the required
data-sharing agreement, and any administrative requirements for releasing this dataset.

Thank you very much for your time, consideration, and leadership in marine fisheries science.

Sincerely,

[TO BE FILLED BY PI — Project Principal Investigator Name]
[TO BE FILLED BY PI — Designation & Institutional Affiliation]
[TO BE FILLED BY PI — Institutional Postal Address]
[TO BE FILLED BY PI — Official Institutional Email Address] | [TO BE FILLED BY PI — Telephone / Mobile]

Date: [TO BE FILLED BY PI — Date of dispatch on letterhead]
```

---

## Part C: Technical Annexure

### 1. Pilot Landing Centers Georeferencing

The coordinates below represent the **landing centers** (harbor/jetty location) where catch is
officially registered. These are NOT fishing ground coordinates. If CMFRI records include
separate fishing-ground positions, both columns should be supplied with explicit field names.

| Landing Center | State | Latitude | Longitude | Primary Fleet / Gear Types | Typical Voyage Profile |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **Malim Jetty (Panaji)** | Goa | $15.5036^\circ\text{N}$ | $73.8286^\circ\text{E}$ | Purse Seiners, Mechanized Trawlers | Single-day neritic to 3-day shelf voyages |
| **Mirkarwada (Ratnagiri)** | Maharashtra | $16.9902^\circ\text{N}$ | $73.2847^\circ\text{E}$ | Trawlers, Gillnetters, Ring Seiners | 1 to 5-day coastal and shelf trips |
| **Sasoon Docks (Mumbai)** | Maharashtra | $18.9167^\circ\text{N}$ | $72.8250^\circ\text{E}$ | Mechanized Multi-day Trawlers, Liners | 5 to 12-day deep-sea shelf break trips |
| **Baithkol (Karwar)** | Karnataka | $14.8055^\circ\text{N}$ | $74.1244^\circ\text{E}$ | Purse Seiners, Motorized Crafts | Single-day pelagic coastal operations |
| **Mangalore (Old Port)** | Karnataka | $12.8580^\circ\text{N}$ | $74.8360^\circ\text{E}$ | Purse Seiners, Deep-sea Trawlers, Longliners | 2 to 10-day offshore pelagic trips |

---

### 2. Species Registry & Cross-Version Code Reconciliation

> [!WARNING]
> **Species-Code Discrepancy Notice — Requires CMFRI Confirmation (Submission Blocker)**
>
> Two species codes are contested between historical project usage and current FAO ASFIS records.
> The software registry registers **both** codes as aliases so import is not blocked, but the
> canonical code used in CMFRI datasets must be confirmed before production data delivery to
> ensure unambiguous CPUE attribution.
>
> | Species | Scientific Name | Current FAO ASFIS Code | Historical Project Code | Status |
> | :--- | :--- | :---: | :---: | :--- |
> | Indian Mackerel | *Rastrelliger kanagurta* | **RAG** | RAK (INCOIS PFZ notation) | **UNRESOLVED — ask CMFRI** |
> | Silver Pomfret | *Pampus argenteus* | **SIP** | POA (older catalog reference) | **UNRESOLVED — ask CMFRI** |
>
> Reference: FAO ASFIS List of Species for Fishery Statistics Purposes
> (https://www.fao.org/fishery/en/collection/asfis/en — verify current revision before submission)

To avoid ambiguity or silent substitution across project releases, the table below reconciles
species common names, scientific names, FAO 3-alpha codes, and historical registry keys:

| Target Species Common Name | Scientific Name | FAO Code (Current) | CMFRI Category | Registry Key | Thermal Range (Optimal) | Cross-Version Status & Notes |
| :--- | :--- | :---: | :--- | :--- | :---: | :--- |
| **Indian Mackerel** | *Rastrelliger kanagurta* | `RAG` *(alias: RAK)* | Pelagic | `mackerel` | $26.0^\circ\text{C} - 30.0^\circ\text{C}$ | Core species (v2.1–v2.8). **Code discrepancy: RAG (FAO ASFIS) vs RAK (INCOIS/historical). CMFRI must confirm.** |
| **Indian Oil Sardine** | *Sardinella longiceps* | `IOS` | Pelagic | `sardine` | $27.0^\circ\text{C} - 30.0^\circ\text{C}$ | Core species (v2.1–v2.8). No code dispute. Upwelling bloom indicator. |
| **Yellowfin Tuna** | *Thunnus albacares* | `YFT` | Oceanic Pelagic | `tuna` | $24.0^\circ\text{C} - 29.0^\circ\text{C}$ | In v2.1–v2.7 grouped under `tuna`. Requested as SEPARATE code `YFT` from CMFRI. No code dispute. |
| **Skipjack Tuna** | *Katsuwonus pelamis* | `SKJ` | Oceanic Pelagic | `skipjack_tuna` | $24.0^\circ\text{C} - 28.5^\circ\text{C}$ | Has dedicated registry key `skipjack_tuna`. Requested as SEPARATE code `SKJ` from CMFRI. No code dispute. |
| **Silver Pomfret** | *Pampus argenteus* | `SIP` *(alias: POA)* | Benthopelagic | `pomfret` | $25.0^\circ\text{C} - 29.5^\circ\text{C}$ | Added v2.7. **Code discrepancy: SIP (FAO ASFIS) vs POA (historical). CMFRI must confirm.** |
| **Bombay Duck** | *Harpadon nehereus* | `DUC` | Demersal | `bombay duck` | $25.0^\circ\text{C} - 29.0^\circ\text{C}$ | Optional demersal baseline, Mumbai/Ratnagiri only. No code dispute. |

> [!NOTE]
> **Yellowfin Tuna and Skipjack Tuna are maintained as SEPARATE canonical species** in the
> ORCA species registry (separate registry keys: `tuna` / `skipjack_tuna`). The requisition
> explicitly requests separate catch and effort line items for `YFT` and `SKJ` from CMFRI.

---

### 3. Canonical CSV Ingestion Schema Specification

The dataset should conform to (or be convertible into) the following schema (13 mandatory schema headers are required for CSV schema parsing; `access_authorization_token` is additionally required for authorized commitment):

| Column Name | Data Type | Mandatory? | Accepted Aliases | Valid Range / Format | Description |
| :--- | :---: | :---: | :--- | :--- | :--- |
| `record_identifier` | String | **YES** | `record_id`, `haul_id`, `trip_id`, `landing_id` | Alphanumeric (non-empty) | Unique landing trip or haul identifier |
| `source_agency` | String | **YES** | `agency`, `institution`, `source` | `"ICAR-CMFRI"` | Data custodian agency |
| `dataset_identifier` | String | **YES** | `dataset_id`, `survey_id`, `batch_id` | Alphanumeric | Versioned collection or export identifier |
| `observation_method` | String | **YES** | `method`, `observation_type` | `COMMERCIAL_LANDING_STATISTIC` | Method classification |
| `species_name` | String | **YES** | `species`, `common_name` | English common name | Species common name |
| `scientific_name` | String | NO | `taxon`, `scientificname` | Valid Latin binomial | Scientific binomial name |
| `fao_alpha3_code` | String | NO | `fao_code`, `species_code` | 3-letter uppercase (`RAG`/`RAK`, `SIP`/`POA`, etc.) | FAO ASFIS species code — see discrepancy notice above |
| `latitude` | Float | **YES** | `lat`, `decimallatitude` | $-90.0$ to $90.0$ (Non-NaN) | **Landing center** latitude (default); note if fishing-ground coordinates are supplied instead |
| `longitude` | Float | **YES** | `lon`, `long`, `decimallongitude` | $-180.0$ to $180.0$ (Non-NaN) | **Landing center** longitude (default); note if fishing-ground coordinates are supplied instead |
| `spatial_uncertainty_km` | Float | NO | `uncertainty_km` | $\ge 0.0$ (Default: $5.0$, max: $50.0$) | Estimated offshore uncertainty radius |
| `landing_center_name` | String | NO | `harbour`, `port`, `landing_site` | Text | Name of landing center |
| `observed_at` | String | **YES** | `event_date`, `landing_date`, `date` | ISO 8601 (`YYYY-MM-DDTHH:MM:SSZ` or `+HH:MM`) | Landing timestamp — UTC preferred; IST with `+05:30` offset is accepted |
| `voyage_start_at` | String | NO | `voyage_start`, `departure_time` | ISO 8601 | Vessel departure timestamp |
| `voyage_end_at` | String | NO | `voyage_end`, `arrival_time` | ISO 8601 | Vessel return timestamp |
| `catch_weight` | Float | **YES** | `catch_kg`, `catch_weight_kg`, `catch` | $\ge 0.0$ (Non-NaN) | Landed weight |
| `catch_unit` | String | **YES** | `unit_catch`, `catch_units` | `"kg"`, `"kilogram"` | Measurement unit for catch — metric tonnes must be flagged separately for conversion |
| `effort_value` | Float | **YES** | `effort_hours`, `duration_hours` | $> 0.0$ (Non-NaN) | Fishing duration in hours (active fishing time, not total voyage duration) |
| `effort_unit` | String | **YES** | `unit_effort`, `effort_units` | `"hours"`, `"hour"`, `"trawl_hours"` | Measurement unit for effort |
| `gear_type` | String | NO | `gear`, `fishing_gear` | Text (e.g. `Purse Seine`, `Trawl`) | Commercial gear used |
| `is_authorized` | Boolean | **YES** | `is_authorized_official_feed`, `authorized` | `true` / `false` | Official authorization flag in CSV — **NOT self-sufficient** |
| `access_authorization_token` | String | **Gate-Enforced (for committed import)** | `auth_token`, `token`, `license_key` | Non-empty string issued by CMFRI/PI | **Out-of-band authorization token — required by authorization gate to commit authorized records (v2.8.1)** |

> [!IMPORTANT]
> **Header requirements & authorization token enforcement (v2.8.1 hardening):**
> 1. **Schema Parsing:** Exactly **13 mandatory schema headers** (`record_identifier`, `source_agency`,
> `dataset_identifier`, `observation_method`, `species_name`, `latitude`, `longitude`, `observed_at`,
> `catch_weight`, `catch_unit`, `effort_value`, `effort_unit`, `is_authorized`) are validated during CSV
> header parsing. Files missing any of these 13 headers are immediately rejected at the schema level.
> 2. **Authorized Commitment:** The `is_authorized=true` flag in a CSV row is NOT sufficient by itself
> to commit a record to the operational biological store. An independently issued `access_authorization_token`
> is additionally required for every authorized row, as enforced by the authorization quality gate (Gate 6).
> This prevents any synthetic or scraping-sourced CSV from bypassing the authorization gate by
> self-declaring its own authorization. The PI / data custodian must supply the token separately
> before real CMFRI data can be ingested.

---

### 4. Catch, Effort & CPUE Formulation

1. **Catch Definition:** Total landed weight in kilograms ($\text{kg}$) for the identified species landed during the trip.
2. **Effort Definition:** Actual cumulative fishing duration in active fishing hours ($\text{hours}$). If only total voyage duration in days is available, voyage days must be converted to estimated effective fishing hours based on CMFRI's standardized fleet factors (to be provided by CMFRI).
3. **Aggregate Records Note:** Monthly aggregate records combine multiple trips. CPUE derived from aggregate records represents the average over all trips in the month, not an individual voyage CPUE. CMFRI's guidance on whether trip-level records are available without privacy constraints is formally requested.
4. **CPUE Calculation:**
   $$\text{CPUE} = \frac{\text{catch\_weight\_kg}}{\text{effort\_hours}} \quad (\text{kg/hour})$$
5. **Safeguard Rules:**
   - Any catch weight $< 0.0$, `NaN`, or `Infinity` is strictly rejected.
   - Any effort hours $\le 0.0$, `NaN`, or `Infinity` is strictly rejected.
   - Unknown units (e.g. "baskets", "boxes") without certified conversion multipliers are rejected with `incompatible_catch_units` or `incompatible_effort_units`.
   - Self-declared authorization without an external token is rejected with `self_declared_authorization_no_external_token`.

---

## Part D: Institutional Contacts Requiring Confirmation

The CMFRI contact information below is sourced from publicly available ICAR-CMFRI institutional
pages. The PI must verify these details are current at the time of submission.

| Role | Organization | Designated Contact Point | Formal Email / Verification Address |
| :--- | :--- | :--- | :--- |
| **Data Custodian (Director)** | ICAR-CMFRI | Director, ICAR-CMFRI, Kochi | `director.cmfri@icar.gov.in` |
| **Division Head** | ICAR-CMFRI | Head, FRAEED Division | `fraeed.cmfri@icar.gov.in` |
| **Data Repository** | ICAR-CMFRI | National Marine Fisheries Data Centre (NMFDC) | `nmfdc.cmfri@icar.gov.in` |
| **Pilot Research Lead** | Project ORCA | **[TO BE FILLED BY PI — Principal Investigator]** | **[TO BE FILLED BY PI — Institutional email]** |
| **Technical Data Custodian** | Project ORCA | **[TO BE FILLED BY PI — Systems Architecture Lead]** | **[TO BE FILLED BY PI — Institutional email]** |

---

## Part E: Submission Blockers Summary

The following items MUST be resolved before transmission. No software change can resolve them.

| # | Blocker | Responsible Party | Nature |
| :-: | :--- | :--- | :--- |
| **B-1** | PI name, designation, institutional affiliation, address, email, and telephone must replace all `[TO BE FILLED BY PI]` placeholders | **Principal Investigator** | Missing real contact details |
| **B-2** | Letter must be printed on official institutional letterhead and signed by the PI | **Principal Investigator** | Institutional endorsement |
| **B-3** | Applicable data-sharing agreement or MOU with CMFRI must be identified and initiated | **PI + Institutional Admin** | Licensing and legal framework |
| **B-4** | CMFRI must confirm preferred 3-alpha code for Indian Mackerel (RAG vs RAK) | **CMFRI / PI** | Species coding discrepancy |
| **B-5** | CMFRI must confirm preferred 3-alpha code for Silver Pomfret (SIP vs POA) | **CMFRI / PI** | Species coding discrepancy |
| **B-6** | Out-of-band `access_authorization_token` must be obtained from CMFRI/PI for each authorized data batch | **PI / CMFRI** | Authorization gate requirement (v2.8.1) |
| **B-7** | CMFRI must confirm whether trip-level or only monthly aggregate records are available for 2023–2025 for the five landing centers | **CMFRI** | Data granularity and CPUE validity |
| **B-8** | CMFRI must confirm whether coordinates in their exports represent the landing center or the fishing ground (or both) | **CMFRI** | Spatial provenance clarification |

---

## Part F: Final Status Classification

| Readiness Dimension | Status | Notes |
| :--- | :---: | :--- |
| **Software pipeline readiness** | `SOFTWARE_DEMO_READY` | Importer, adapter, quality gates, and all 41 regression tests pass (v2.8.1). Authorization bypass fix verified. |
| **Requisition package readiness** | `DRAFT_COMPLETE — AWAITING PI REVIEW` | Package prepared and corrected; requires PI completion and signature before transmission. |
| **Institutional authorization** | `NOT_INITIATED` | No MOU or data-sharing agreement has been concluded with CMFRI. |
| **Biological data receipt** | `AWAITING_AUTHORIZED_DATA` | Zero records in operational store. No CMFRI data has been received or claimed. |
| **Biological predictive accuracy** | `NOT_EVALUABLE` | Withheld until independent authorized ground-truth labels are received, imported, and evaluated. |

> [!NOTE]
> Software readiness (`SOFTWARE_DEMO_READY`) and scientific validation readiness
> (`NOT_EVALUABLE`) are SEPARATE and INDEPENDENT classifications.
> Passing all software tests does not constitute or imply any scientific validation claim.
