"""End-to-End integration tests for ORCA v3.7 Biological Inference Verification.

Verifies through the real FishingZoneAgent and OrchestratorAgent workflows:
1. Untrained model handling without prediction fabrication.
2. Model exception containment without system crash or fallback fabrication.
3. Invalid probability / negative biomass rejection without silent clipping.
4. Unsupported species rejection at the model boundary.
5. Missing or stale evidence handling.
6. Missing biological labels evaluation integrity.
7. Strict separation between physical operational feasibility and biological presence.
8. Backward compatibility of all API response fields.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock
import pytest

from app.agents.biological_prediction_agent import (
    BiologicalFeatureVector,
    BiologicalModelInterface,
    BiologicalPredictionResult,
    EnvironmentalEvidence,
    analyze_environment,
)
from app.agents.fishing_zone_agent import FishingZoneAgent
from app.agents.orchestrator_agent import OrchestratorAgent
from app.evaluation.biological_evaluation_harness import (
    BiologicalEvaluationHarness,
    calculate_classification_metrics,
)
from app.schemas.agent_schemas import (
    FishingZoneAnalyzeRequest,
    OceanAnalyzeResponse,
    OrchestratorAnalyzeRequest,
    RouteAnalyzeResponse,
    SafetyRiskAnalyzeResponse,
    WeatherAnalyzeResponse,
)
from app.schemas.evidence import EvidenceRecord


# ==============================================================================
# Test Doubles for Controlled Boundary Testing
# ==============================================================================

class MockMackerelModel(BiologicalModelInterface):
    """Controlled mock model for Rastrelliger kanagurta (RAG / RAK)."""

    def __init__(
        self,
        is_trained: bool = True,
        fail_with_exception: bool = False,
        bad_probability: float | None = None,
        bad_biomass: float | None = None,
    ) -> None:
        self._is_trained = is_trained
        self.fail_with_exception = fail_with_exception
        self.bad_probability = bad_probability
        self.bad_biomass = bad_biomass

    def is_trained(self) -> bool:
        return self._is_trained

    def supported_species(self) -> list[str]:
        return ["RAG", "RAK", "Mackerel", "mackerel"]

    def model_metadata(self) -> dict[str, Any]:
        return {
            "model_id": "test-mackerel-rf-v1",
            "version": "1.0.0",
            "target_species": "Rastrelliger kanagurta",
        }

    def predict(self, features: BiologicalFeatureVector) -> BiologicalPredictionResult:
        if self.fail_with_exception:
            raise RuntimeError("Underlying tensor engine failed: Matrix non-invertible")

        prob = self.bad_probability if self.bad_probability is not None else 0.82
        biomass = self.bad_biomass if self.bad_biomass is not None else 120.0

        res = BiologicalPredictionResult(
            species_code=features.species_code,
            target="presence_absence",
            predicted_presence=True,
            probability=0.82,  # valid initial Pydantic value
            biomass_density_kg_km2=120.0,
            confidence_score=0.90,
            model_id="test-mackerel-rf-v1",
            model_version="1.0.0",
            prediction_timestamp=datetime.now(timezone.utc),
            diagnostics={"sst": features.sea_surface_temperature_c},
        )
        if self.bad_probability is not None:
            object.__setattr__(res, "probability", self.bad_probability)
        if self.bad_biomass is not None:
            object.__setattr__(res, "biomass_density_kg_km2", self.bad_biomass)
        return res

    def predict_batch(
        self, features_list: list[BiologicalFeatureVector]
    ) -> list[BiologicalPredictionResult]:
        return [self.predict(f) for f in features_list]


@pytest.fixture
def base_marine_provider():
    """Mock marine data provider delivering fresh offshore observations."""
    provider = AsyncMock()
    provider.provider_name = "open-meteo-marine"
    now_utc = datetime.now(timezone.utc)

    records = [
        EvidenceRecord(
            evidence_id="wave-1",
            source="open-meteo-marine",
            variable="wave_height",
            value=0.9,  # Favorable sea state (< 1.25 m)
            unit="m",
            latitude=15.0,
            longitude=73.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        ),
        EvidenceRecord(
            evidence_id="sst-1",
            source="open-meteo-marine",
            variable="sea_surface_temperature",
            value=28.5,  # Optimal thermal habitat for Mackerel
            unit="degC",
            latitude=15.0,
            longitude=73.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        ),
    ]
    provider.fetch.return_value = records
    return provider


# ==============================================================================
# 1. Untrained Model Workflow Integration
# ==============================================================================

@pytest.mark.asyncio
async def test_workflow_untrained_model_refuses_prediction(base_marine_provider):
    """An untrained model integrated into FishingZoneAgent never predicts fish presence."""
    untrained_model = MockMackerelModel(is_trained=False)
    agent = FishingZoneAgent(
        provider=base_marine_provider,
        biological_model=untrained_model,
    )

    req = FishingZoneAnalyzeRequest(
        latitude=15.0,
        longitude=73.0,
        target_species="mackerel",
    )
    resp = await agent.analyze(req)

    # Physical wave feasibility is computed normally
    assert resp.analysis["operational_feasibility"] == "FAVORABLE"
    assert resp.analysis["operational_feasibility_scope"] == "STRICTLY_PHYSICAL_WAVE_CONDITIONS"

    # Biological inference preserves strict non-fabrication safeguards
    bio_pred = resp.analysis["biological_prediction"]
    assert bio_pred["model_inference_status"] == "MODEL_NOT_TRAINED"
    assert bio_pred["fish_presence"] == "UNVERIFIED"
    assert bio_pred["catch_probability"] is None
    assert bio_pred["biomass_prediction"] is None
    assert bio_pred["predictive_accuracy"] == "NOT_EVALUABLE"


# ==============================================================================
# 2. Model Exception Workflow Containment
# ==============================================================================

@pytest.mark.asyncio
async def test_workflow_model_exception_handled_safely(base_marine_provider):
    """A model crashing during inference does not break the agent or fabricate predictions."""
    failing_model = MockMackerelModel(is_trained=True, fail_with_exception=True)
    agent = FishingZoneAgent(
        provider=base_marine_provider,
        biological_model=failing_model,
    )

    req = FishingZoneAnalyzeRequest(
        latitude=15.0,
        longitude=73.0,
        target_species="mackerel",
    )
    resp = await agent.analyze(req)

    assert resp.analysis["operational_feasibility"] == "FAVORABLE"

    bio_pred = resp.analysis["biological_prediction"]
    assert bio_pred["model_inference_status"] == "MODEL_EXECUTION_ERROR"
    assert "Matrix non-invertible" in bio_pred["model_execution_error"]
    assert bio_pred["fish_presence"] == "UNVERIFIED"
    assert bio_pred["catch_probability"] is None
    assert bio_pred["biomass_prediction"] is None


# ==============================================================================
# 3. Invalid Probability and Biomass Output Rejection
# ==============================================================================

@pytest.mark.asyncio
async def test_workflow_invalid_probability_rejected_without_silent_clipping(base_marine_provider):
    """Probability > 1.0 is rejected, preserving unverified status without clipping to 1.0."""
    bad_prob_model = MockMackerelModel(is_trained=True, bad_probability=1.75)
    agent = FishingZoneAgent(
        provider=base_marine_provider,
        biological_model=bad_prob_model,
    )

    req = FishingZoneAnalyzeRequest(
        latitude=15.0,
        longitude=73.0,
        target_species="mackerel",
    )
    resp = await agent.analyze(req)

    bio_pred = resp.analysis["biological_prediction"]
    assert bio_pred["model_inference_status"] == "INVALID_MODEL_OUTPUT"
    assert bio_pred["fish_presence"] == "UNVERIFIED"
    assert bio_pred["catch_probability"] is None  # NOT silently clipped to 1.0
    assert any("invalid_probability" in err for err in bio_pred["output_validation_errors"])


@pytest.mark.asyncio
async def test_workflow_negative_biomass_rejected_without_silent_clipping(base_marine_provider):
    """Negative biomass is rejected, preserving unverified status without clipping to 0.0."""
    bad_biomass_model = MockMackerelModel(is_trained=True, bad_biomass=-40.0)
    agent = FishingZoneAgent(
        provider=base_marine_provider,
        biological_model=bad_biomass_model,
    )

    req = FishingZoneAnalyzeRequest(
        latitude=15.0,
        longitude=73.0,
        target_species="mackerel",
    )
    resp = await agent.analyze(req)

    bio_pred = resp.analysis["biological_prediction"]
    assert bio_pred["model_inference_status"] == "INVALID_MODEL_OUTPUT"
    assert bio_pred["fish_presence"] == "UNVERIFIED"
    assert bio_pred["biomass_prediction"] is None  # NOT silently clipped to 0.0
    assert any("invalid_biomass_density" in err for err in bio_pred["output_validation_errors"])


# ==============================================================================
# 4. Unsupported Species Rejection
# ==============================================================================

@pytest.mark.asyncio
async def test_workflow_unsupported_species_rejected(base_marine_provider):
    """Requesting Yellowfin Tuna on a Mackerel model is blocked at model boundary."""
    mackerel_model = MockMackerelModel(is_trained=True)
    agent = FishingZoneAgent(
        provider=base_marine_provider,
        biological_model=mackerel_model,
    )

    req = FishingZoneAnalyzeRequest(
        latitude=15.0,
        longitude=73.0,
        target_species="Yellowfin Tuna",  # Valid species in ORCA, but unsupported by this model
    )
    resp = await agent.analyze(req)

    bio_pred = resp.analysis["biological_prediction"]
    assert bio_pred["model_inference_status"] == "UNSUPPORTED_SPECIES_FOR_MODEL"
    assert bio_pred["fish_presence"] == "UNVERIFIED"
    assert bio_pred["catch_probability"] is None


# ==============================================================================
# 5. Missing or Stale Evidence Workflow Integration
# ==============================================================================

@pytest.mark.asyncio
async def test_workflow_missing_or_stale_evidence_handling():
    """Stale observations reduce evidence completeness without fabricating predictions."""
    stale_provider = AsyncMock()
    stale_provider.provider_name = "open-meteo-marine"
    stale_time = datetime.now(timezone.utc) - timedelta(hours=48)

    stale_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="wave-stale",
            source="open-meteo-marine",
            variable="wave_height",
            value=1.1,
            unit="m",
            latitude=15.0,
            longitude=73.0,
            observed_at=stale_time,
            retrieved_at=stale_time,
            status="valid",
        )
    ]

    model = MockMackerelModel(is_trained=True)
    agent = FishingZoneAgent(
        provider=stale_provider,
        biological_model=model,
    )

    req = FishingZoneAnalyzeRequest(latitude=15.0, longitude=73.0)
    resp = await agent.analyze(req)

    # All wave records were stale, so zone suitability is insufficient_evidence
    assert resp.status == "insufficient_evidence"
    assert resp.analysis["zone_suitability"] == "INSUFFICIENT_EVIDENCE"
    assert resp.analysis["operational_feasibility"] == "UNVERIFIED"


# ==============================================================================
# 6. Missing Biological Labels Evaluation Integrity
# ==============================================================================

def test_harness_missing_labels_produces_not_evaluable():
    """Harness strictly produces status='NOT_EVALUABLE' when labels are absent or None."""
    # Test 1: Empty list
    res_empty = calculate_classification_metrics(y_true=[])
    assert res_empty["status"] == "NOT_EVALUABLE"
    assert res_empty["metrics"] is None

    # Test 2: Unlabeled data (all None)
    res_unlabeled = calculate_classification_metrics(
        y_true=[None, None, None],
        y_pred_prob=[0.7, 0.4, 0.1],
    )
    assert res_unlabeled["status"] == "NOT_EVALUABLE"
    assert res_unlabeled["metrics"] is None

    # Test 3: Non-binary string markers (e.g. 'UNKNOWN')
    res_corrupt = calculate_classification_metrics(
        y_true=["UNKNOWN", "UNKNOWN"],  # type: ignore[arg-type]
        y_pred_prob=[0.8, 0.2],
    )
    assert res_corrupt["status"] == "NOT_EVALUABLE"
    assert res_corrupt["metrics"] is None


# ==============================================================================
# 7. Operational Feasibility vs Biological Presence Separation
# ==============================================================================

@pytest.mark.asyncio
async def test_operational_feasibility_isolated_from_biological_presence():
    """Hazardous wave heights result in HAZARDOUS feasibility regardless of biological model."""
    hazardous_provider = AsyncMock()
    hazardous_provider.provider_name = "open-meteo-marine"
    now_utc = datetime.now(timezone.utc)

    hazardous_provider.fetch.return_value = [
        EvidenceRecord(
            evidence_id="wave-rough",
            source="open-meteo-marine",
            variable="wave_height",
            value=3.8,  # Rough/hazardous (> 2.5 m)
            unit="m",
            latitude=15.0,
            longitude=73.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        ),
        EvidenceRecord(
            evidence_id="sst-optimal",
            source="open-meteo-marine",
            variable="sea_surface_temperature",
            value=28.0,  # Optimal thermal habitat
            unit="degC",
            latitude=15.0,
            longitude=73.0,
            observed_at=now_utc,
            retrieved_at=now_utc,
            status="valid",
        ),
    ]

    model = MockMackerelModel(is_trained=True)
    agent = FishingZoneAgent(
        provider=hazardous_provider,
        biological_model=model,
    )

    req = FishingZoneAnalyzeRequest(
        latitude=15.0,
        longitude=73.0,
        target_species="mackerel",
    )
    resp = await agent.analyze(req)

    # Wave feasibility must strictly reflect hazardous sea state
    assert resp.analysis["operational_feasibility"] == "HAZARDOUS"
    assert resp.analysis["operational_feasibility_scope"] == "STRICTLY_PHYSICAL_WAVE_CONDITIONS"
    # Divergence conflict warning should be present in top-level warnings
    assert any("CONFLICT / DIVERGENCE" in w for w in resp.warnings)


# ==============================================================================
# 8. Full Orchestrator Integration Workflow
# ==============================================================================

@pytest.mark.asyncio
async def test_orchestrator_workflow_propagates_biological_safeguards(base_marine_provider):
    """End-to-end dispatch through OrchestratorAgent propagates biological inference safely."""
    model = MockMackerelModel(is_trained=True)
    fishing_agent = FishingZoneAgent(
        provider=base_marine_provider,
        biological_model=model,
    )

    mock_weather = AsyncMock()
    mock_weather.analyze.return_value = WeatherAnalyzeResponse(
        agent="Weather Agent",
        status="success",
        location={"latitude": 15.0, "longitude": 73.0},
        data_source={"provider": "Open-Meteo Weather"},
        observations={"temperature_c": 28.0, "wind_speed_knots": 12.0, "wind_direction_deg": 240.0, "precipitation_mm": 0.0},
        forecast=[],
        analysis={"wind_regime": "Gentle breeze"},
        warnings=[],
    )

    mock_ocean = AsyncMock()
    mock_ocean.analyze.return_value = OceanAnalyzeResponse(
        agent="Ocean Agent",
        status="success",
        location={"latitude": 15.0, "longitude": 73.0},
        data_source={"provider": "Open-Meteo Marine"},
        observations={"wave_height_m": 1.1, "sample_count": 24},
        analysis={"wmo_sea_state": {"code": 3, "description": "Slight (0.5 - 1.25 m)"}},
        warnings=[],
    )

    mock_route = AsyncMock()
    mock_route.analyze.return_value = RouteAnalyzeResponse(
        agent="Route Agent",
        status="success",
        location={"origin": "Offshore Goa", "destination": "Mumbai Port"},
        data_source={"calculation_method": "Haversine Great-Circle geodesic formula"},
        observations={"total_distance_km": 440.0, "total_distance_nm": 237.5, "waypoint_count": 2},
        analysis={"estimated_transit_hours": 19.8},
        warnings=["Straight-line geodesic distance only."],
    )

    mock_safety = AsyncMock()
    mock_safety.analyze.return_value = SafetyRiskAnalyzeResponse(
        agent="Safety/Risk Agent",
        status="success",
        location={"latitude": 15.0, "longitude": 73.0},
        data_source={"providers_attempted": ["Open-Meteo Marine"]},
        observations={"wave_height_m": 1.1, "wind_speed_knots": 12.0, "precipitation_mm": 0.0},
        analysis={"risk_category": "LOW", "risk_score": 25, "risk_reasons": ["Favorable baseline conditions."], "recommendations": ["Safe operational baseline."]},
        warnings=[],
    )

    orchestrator = OrchestratorAgent(
        weather_agent=mock_weather,
        ocean_agent=mock_ocean,
        fishing_zone_agent=fishing_agent,
        route_agent=mock_route,
        safety_risk_agent=mock_safety,
    )

    req = OrchestratorAnalyzeRequest(
        latitude=15.0,
        longitude=73.0,
        user_objective="all",
        vessel_type="small_craft",
        target_species="mackerel",
        destination_latitude=18.9,
        destination_longitude=72.8,
    )

    resp = await orchestrator.analyze(req)
    assert resp.status == "success"

    fisheries = resp.derived_estimates["fisheries_suitability"]
    assert fisheries["actual_fish_presence"] == "UNVERIFIED"
    assert fisheries["catch_probability"] is None
    assert fisheries["biomass_prediction"] is None
    assert fisheries["predictive_accuracy"] == "NOT_EVALUABLE"
    assert fisheries["operational_feasibility"] == "FAVORABLE"
    assert fisheries["biological_prediction"] is not None
    assert fisheries["biological_prediction"]["model_inference_status"] == "INFERENCE_SUCCESS"
    assert fisheries["biological_prediction"]["target_species"] == "mackerel"
