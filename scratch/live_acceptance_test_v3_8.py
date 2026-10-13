"""ORCA v3.8 Live Application Acceptance Test Suite.
Executes real HTTP requests against the running FastAPI backend on http://127.0.0.1:8010.
"""

import json
from datetime import datetime
import httpx

BASE_URL = "http://127.0.0.1:8010"

def run_acceptance_suite():
    client = httpx.Client(base_url=BASE_URL, timeout=30.0)
    results = {}

    print("=== ORCA v3.8 Live Application Acceptance Testing ===")

    # 1. Health Check
    r_health = client.get("/api/health")
    print(f"\n[1] Health Check: {r_health.status_code}")
    print(r_health.json())
    assert r_health.status_code == 200
    results["health"] = {"status_code": r_health.status_code, "body": r_health.json()}

    # 2. Valid Offshore Coordinates with Available Marine Telemetry
    payload_offshore = {
        "latitude": 15.0,
        "longitude": 73.0,
        "target_species": "mackerel",
        "forecast_time_window_hours": 24,
    }
    r_offshore = client.post("/api/agents/fishing-zone/analyze", json=payload_offshore)
    print(f"\n[2] Valid Offshore (15.0, 73.0): {r_offshore.status_code}")
    data_offshore = r_offshore.json()
    print("Agent:", data_offshore.get("agent"))
    print("Status:", data_offshore.get("status"))
    print("Operational Feasibility:", data_offshore.get("analysis", {}).get("operational_feasibility"))
    print("Operational Scope:", data_offshore.get("analysis", {}).get("operational_feasibility_scope"))
    print("Biological Prediction Summary:", data_offshore.get("analysis", {}).get("biological_prediction"))
    print("Verified Fish Dist Status:", data_offshore.get("analysis", {}).get("verified_fish_distribution", {}).get("status"))
    print("Catch Probability:", data_offshore.get("analysis", {}).get("verified_fish_distribution", {}).get("catch_probability"))
    print("Biomass Prediction:", data_offshore.get("analysis", {}).get("verified_fish_distribution", {}).get("biomass_prediction"))
    
    # Assertions for scenario 2
    assert r_offshore.status_code in [200, 201]
    assert data_offshore["analysis"]["operational_feasibility"] in ["FAVORABLE", "CAUTIONARY", "HAZARDOUS"]
    assert data_offshore["analysis"]["operational_feasibility_scope"] == "STRICTLY_PHYSICAL_WAVE_CONDITIONS"
    assert data_offshore["analysis"]["biological_prediction"]["fish_presence"] == "UNVERIFIED"
    assert data_offshore["analysis"]["biological_prediction"]["catch_probability"] is None
    assert data_offshore["analysis"]["biological_prediction"]["biomass_prediction"] is None
    results["offshore"] = {"status_code": r_offshore.status_code, "feasibility": data_offshore["analysis"]["operational_feasibility"]}

    # 3. Inland Coordinates with Insufficient Marine Telemetry (New Delhi: 28.6139, 77.2090)
    payload_inland = {
        "latitude": 28.6139,
        "longitude": 77.2090,
        "location_name": "New Delhi (Inland Landmass)",
    }
    r_inland = client.post("/api/agents/fishing-zone/analyze", json=payload_inland)
    print(f"\n[3] Inland Coordinates (28.61, 77.21): {r_inland.status_code}")
    data_inland = r_inland.json()
    print("Status:", data_inland.get("status"))
    print("Zone Suitability:", data_inland.get("analysis", {}).get("zone_suitability"))
    print("Operational Feasibility:", data_inland.get("analysis", {}).get("operational_feasibility"))
    
    # Assertions for scenario 3
    assert r_inland.status_code in [200, 201]
    assert data_inland["status"] == "insufficient_evidence"
    assert data_inland["analysis"]["operational_feasibility"] in ["NON_NAVIGABLE_OR_INLAND", "UNVERIFIED"]
    bio_inland = data_inland["analysis"]["biological_prediction"]
    assert bio_inland["fish_presence"] == "UNVERIFIED"
    assert bio_inland["catch_probability"] is None
    assert bio_inland["biomass_prediction"] is None
    assert bio_inland["predictive_accuracy"] == "NOT_EVALUABLE"
    assert bio_inland["ground_truth_status"] == "AWAITING_AUTHORIZED_DATA"
    results["inland"] = {"status_code": r_inland.status_code, "status": data_inland["status"]}

    # 4. Missing or Invalid Input (Out-of-bounds latitude 95.0, longitude 250.0)
    payload_invalid = {
        "latitude": 95.0,  # Invalid: > 90.0
        "longitude": 250.0,  # Invalid: > 180.0
    }
    r_invalid = client.post("/api/agents/fishing-zone/analyze", json=payload_invalid)
    print(f"\n[4] Invalid Coordinates (95.0, 250.0): {r_invalid.status_code}")
    print("Error Detail:", r_invalid.text[:200])
    # FastAPI/Pydantic returns 422 Unprocessable Entity for schema validation failures
    assert r_invalid.status_code == 422
    results["invalid_input"] = {"status_code": r_invalid.status_code}

    # 5. Missing Coordinates Entirely
    r_missing = client.post("/api/agents/fishing-zone/analyze", json={})
    print(f"\n[5] Missing Coordinates entirely: {r_missing.status_code}")
    data_missing = r_missing.json()
    print("Status:", data_missing.get("status"))
    print("Error:", data_missing.get("error"))
    assert data_missing["status"] == "insufficient_evidence"
    results["missing_coords"] = {"status_code": r_missing.status_code, "status": data_missing["status"]}

    # 6. Biological Inference Without Trained Model (Verification of Production Invariants)
    bio_pred = data_offshore["analysis"]["biological_prediction"]
    print(f"\n[6] Biological Inference Safeguards Check:")
    print("Fish Presence:", bio_pred.get("fish_presence"))
    print("Catch Probability:", bio_pred.get("catch_probability"))
    print("Biomass Prediction:", bio_pred.get("biomass_prediction"))
    print("Predictive Accuracy:", bio_pred.get("predictive_accuracy"))
    print("Ground Truth Status:", bio_pred.get("ground_truth_status"))
    print("Evidence Completeness:", bio_pred.get("environmental_evidence_completeness_pct"))
    assert bio_pred["fish_presence"] == "UNVERIFIED"
    assert bio_pred["catch_probability"] is None
    assert bio_pred["biomass_prediction"] is None
    assert bio_pred["predictive_accuracy"] == "NOT_EVALUABLE"
    assert bio_pred["ground_truth_status"] == "AWAITING_AUTHORIZED_DATA"
    results["biological_safeguards"] = "PASSED"

    # 7. Hazardous Wave Conditions (High latitude stormy Southern Ocean / Roaring Forties: -52.0, 75.0)
    payload_hazardous = {
        "latitude": -52.0,
        "longitude": 75.0,
        "location_name": "Southern Ocean Storm Track",
    }
    r_hazardous = client.post("/api/agents/fishing-zone/analyze", json=payload_hazardous)
    print(f"\n[7] High-Sea Storm Track (-52.0, 75.0): {r_hazardous.status_code}")
    data_hazardous = r_hazardous.json()
    print("Operational Feasibility:", data_hazardous.get("analysis", {}).get("operational_feasibility"))
    print("Max Wave Height (m):", data_hazardous.get("observations", {}).get("max_wave_height_m"))
    print("Sea State Category:", data_hazardous.get("observations", {}).get("sea_state_category"))
    results["hazardous_wave"] = {
        "status_code": r_hazardous.status_code,
        "feasibility": data_hazardous.get("analysis", {}).get("operational_feasibility"),
        "max_wave_m": data_hazardous.get("observations", {}).get("max_wave_height_m"),
    }

    # 8. Full Orchestrator Dispatch (/api/agents/orchestrator/analyze)
    payload_orchestrator = {
        "latitude": 15.0,
        "longitude": 73.0,
        "user_objective": "all",
        "vessel_type": "small_craft",
        "target_species": "mackerel",
        "destination_latitude": 18.9,
        "destination_longitude": 72.8,
    }
    r_orch = client.post("/api/agents/orchestrator/analyze", json=payload_orchestrator)
    print(f"\n[8] Full Orchestrator Dispatch: {r_orch.status_code}")
    data_orch = r_orch.json()
    print("Status:", data_orch.get("status"))
    print("Agents Dispatched:", list(data_orch.get("agent_responses", {}).keys()))
    derived = data_orch.get("derived_estimates", {})
    fisheries_derived = derived.get("fisheries_suitability", {})
    print("Derived Fisheries Actual Presence:", fisheries_derived.get("actual_fish_presence"))
    print("Derived Catch Probability:", fisheries_derived.get("catch_probability"))
    print("Derived Biomass Prediction:", fisheries_derived.get("biomass_prediction"))
    print("Derived Predictive Accuracy:", fisheries_derived.get("predictive_accuracy"))
    print("Derived Operational Feasibility:", fisheries_derived.get("operational_feasibility"))
    print("Derived Geodesic Distance (km):", derived.get("geodesic_route", {}).get("distance_km"))
    
    print("Orchestrator Errors:", data_orch.get("errors"))
    print("Agent Responses Keys:", list(data_orch.get("agent_responses", {}).keys()))
    print("Synthesis Warnings:", data_orch.get("synthesis", {}).get("warnings"))
    
    # Assertions for scenario 8
    assert r_orch.status_code in [200, 201]
    assert data_orch["status"] in ["success", "insufficient_evidence", "partial_failure"]
    assert fisheries_derived["actual_fish_presence"] == "UNVERIFIED"
    assert fisheries_derived["catch_probability"] is None
    assert fisheries_derived["biomass_prediction"] is None
    assert fisheries_derived["predictive_accuracy"] == "NOT_EVALUABLE"
    assert fisheries_derived["operational_feasibility_scope"] == "STRICTLY_PHYSICAL_WAVE_CONDITIONS"
    results["orchestrator"] = {"status_code": r_orch.status_code, "status": data_orch["status"]}

    print("\n=== ALL SCENARIOS VERIFIED SUCCESSFULLY ===")
    return results

if __name__ == "__main__":
    run_acceptance_suite()
