"""Unit tests for Biological Model Interface, Feature Validation Contract, and Evaluation Harness.

Validates:
1. Feature contract physical and biological boundary validation (SST, Chlorophyll, Salinity, Species, Coordinates).
2. Future-dated observation rejection in feature contract.
3. Temporal train/test splitting with zero temporal leakage verification.
4. Spatial block holdout splitting without cross-block contamination.
5. Truthful evaluation metrics: status='NOT_EVALUABLE' when labels are absent.
6. Binary classification metric calculations (Accuracy, Precision, Recall, F1, Brier Score) with safe denominators.
7. BiologicalModelInterface contract enforcement and inference integration in analyze_environment.
8. Preservation of environmental completeness isolation (completeness never fabricates fish presence).
"""

from datetime import datetime, timedelta, timezone
from typing import Any
import pytest

from app.agents.biological_prediction_agent import (
    BiologicalFeatureContract,
    BiologicalFeatureVector,
    BiologicalModelInterface,
    BiologicalPredictionResult,
    EnvironmentalEvidence,
    analyze_environment,
)
from app.evaluation.biological_evaluation_harness import (
    BiologicalEvaluationHarness,
    calculate_classification_metrics,
    spatial_block_split,
    temporal_train_test_split,
)


class DummyTrainedBiologicalModel(BiologicalModelInterface):
    """Test double implementing BiologicalModelInterface for unit testing."""

    def __init__(self, is_trained: bool = True, model_id: str = "mock-mackerel-v1.0") -> None:
        self._is_trained = is_trained
        self.model_id = model_id

    def is_trained(self) -> bool:
        return self._is_trained

    def supported_species(self) -> list[str]:
        return ["RAG", "RAK"]

    def model_metadata(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "version": "1.0.0",
            "target_species": "Rastrelliger kanagurta",
            "training_algorithm": "MockLogisticRegression",
        }

    def predict(self, features: BiologicalFeatureVector) -> BiologicalPredictionResult:
        # Simple deterministic rule for mock: SST between 26 and 30 C -> presence
        sst = features.sea_surface_temperature_c
        is_present = sst is not None and 26.0 <= sst <= 30.0
        prob = 0.85 if is_present else 0.15
        return BiologicalPredictionResult(
            species_code=features.species_code,
            target="presence_absence",
            predicted_presence=is_present,
            probability=prob,
            confidence_score=0.90,
            model_id=self.model_id,
            model_version="1.0.0",
            prediction_timestamp=datetime.now(timezone.utc),
            diagnostics={"sst_evaluated": sst},
        )

    def predict_batch(
        self, features_list: list[BiologicalFeatureVector]
    ) -> list[BiologicalPredictionResult]:
        return [self.predict(f) for f in features_list]


# ==============================================================================
# 1. Feature Contract & Physical Bounds Tests
# ==============================================================================

def test_feature_vector_validation_success():
    """Valid feature vector with registered species and valid marine SST passes contract."""
    vec = BiologicalFeatureVector(
        species_code="RAG",
        latitude=15.5,
        longitude=73.5,
        observed_at=datetime(2026, 10, 12, 10, 0, 0, tzinfo=timezone.utc),
        sea_surface_temperature_c=28.4,
        chlorophyll_a_mg_m3=1.2,
        salinity_psu=34.5,
    )
    is_valid, errors = BiologicalFeatureContract.validate_features(
        vec,
        now=datetime(2026, 10, 13, 0, 0, 0, tzinfo=timezone.utc),
    )
    assert is_valid is True
    assert errors == []


def test_feature_vector_validation_unsupported_species():
    """Unregistered species code is rejected by feature contract."""
    vec = BiologicalFeatureVector(
        species_code="UNKNOWN_FISH_999",
        latitude=15.5,
        longitude=73.5,
        observed_at=datetime(2026, 10, 12, 10, 0, 0, tzinfo=timezone.utc),
        sea_surface_temperature_c=28.0,
    )
    is_valid, errors = BiologicalFeatureContract.validate_features(vec)
    assert is_valid is False
    assert any("unsupported_species" in e for e in errors)


def test_feature_vector_validation_future_date_rejected():
    """Observation dated in the future relative to evaluation clock is rejected."""
    vec = BiologicalFeatureVector(
        species_code="RAG",
        latitude=15.5,
        longitude=73.5,
        observed_at=datetime(2026, 10, 20, 0, 0, 0, tzinfo=timezone.utc),
        sea_surface_temperature_c=28.0,
    )
    is_valid, errors = BiologicalFeatureContract.validate_features(
        vec,
        now=datetime(2026, 10, 13, 0, 0, 0, tzinfo=timezone.utc),
    )
    assert is_valid is False
    assert any("future_dated_observation" in e for e in errors)


def test_feature_vector_validation_unphysical_sst_rejected():
    """Unphysical marine temperature (e.g. 55 C) violates physical contract."""
    vec = BiologicalFeatureVector(
        species_code="RAG",
        latitude=15.5,
        longitude=73.5,
        observed_at=datetime(2026, 10, 12, 10, 0, 0, tzinfo=timezone.utc),
        sea_surface_temperature_c=55.0,  # Unphysical for marine sea surface
    )
    is_valid, errors = BiologicalFeatureContract.validate_features(
        vec,
        now=datetime(2026, 10, 13, 0, 0, 0, tzinfo=timezone.utc),
    )
    assert is_valid is False
    assert any("unphysical_sst" in e for e in errors)


def test_feature_vector_validation_missing_required_feature():
    """When a model declares mandatory features, missing values are flagged."""
    vec = BiologicalFeatureVector(
        species_code="RAG",
        latitude=15.5,
        longitude=73.5,
        observed_at=datetime(2026, 10, 12, 10, 0, 0, tzinfo=timezone.utc),
        sea_surface_temperature_c=28.0,
        chlorophyll_a_mg_m3=None,  # Missing
    )
    is_valid, errors = BiologicalFeatureContract.validate_features(
        vec,
        required_features=["chlorophyll_a_mg_m3"],
        now=datetime(2026, 10, 13, 0, 0, 0, tzinfo=timezone.utc),
    )
    assert is_valid is False
    assert any("missing_required_feature" in e for e in errors)


# ==============================================================================
# 2. Leakage-Free Data Splitting Tests
# ==============================================================================

def test_temporal_train_test_split_zero_leakage():
    """Temporal split guarantees that max(train_time) < min(test_time)."""
    base_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    records = [
        {"id": i, "observed_at": base_time + timedelta(days=i * 5), "val": i}
        for i in range(20)
    ]

    train, test = temporal_train_test_split(records, test_ratio=0.25)
    assert len(train) == 15
    assert len(test) == 5

    max_train_time = max(r["observed_at"] for r in train)
    min_test_time = min(r["observed_at"] for r in test)
    assert max_train_time < min_test_time


def test_temporal_train_test_split_with_explicit_cutoff():
    """Temporal split with explicit cutoff cleanly divides around timestamp threshold."""
    cutoff = datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    records = [
        {"id": 1, "observed_at": datetime(2026, 3, 1, tzinfo=timezone.utc)},
        {"id": 2, "observed_at": datetime(2026, 5, 15, tzinfo=timezone.utc)},
        {"id": 3, "observed_at": datetime(2026, 7, 1, tzinfo=timezone.utc)},
        {"id": 4, "observed_at": datetime(2026, 8, 1, tzinfo=timezone.utc)},
    ]

    train, test = temporal_train_test_split(records, cutoff_time=cutoff)
    assert len(train) == 2
    assert len(test) == 2
    assert [r["id"] for r in train] == [1, 2]
    assert [r["id"] for r in test] == [3, 4]


def test_spatial_block_split_partitions_blocks():
    """Spatial block holdout partitions distinct geographic grid squares."""
    records = [
        {"id": "NW1", "latitude": 18.0, "longitude": 70.0},
        {"id": "NW2", "latitude": 18.5, "longitude": 70.5},
        {"id": "SE1", "latitude": 10.0, "longitude": 76.0},
        {"id": "SE2", "latitude": 10.5, "longitude": 76.5},
    ]

    folds = spatial_block_split(records, n_blocks_lat=2, n_blocks_lon=2)
    assert len(folds) >= 2
    for train, test in folds:
        assert len(train) > 0
        assert len(test) > 0
        # Assert no ID in test exists in train
        train_ids = {r["id"] for r in train}
        test_ids = {r["id"] for r in test}
        assert train_ids.isdisjoint(test_ids)


# ==============================================================================
# 3. Scientific Truthfulness & Metric Calculation Tests
# ==============================================================================

def test_metrics_calculation_empty_labels_withheld():
    """Zero ground-truth labels explicitly returns status='NOT_EVALUABLE' and metrics=None."""
    result = calculate_classification_metrics(y_true=[])
    assert result["status"] == "NOT_EVALUABLE"
    assert result["metrics"] is None
    assert "Zero verified ground-truth labels" in result["reason"]


def test_metrics_calculation_standard_binary_metrics():
    """Verified labels produce mathematically exact Accuracy, Precision, Recall, and F1."""
    y_true = [1, 1, 0, 0, 1]
    y_prob = [0.9, 0.8, 0.2, 0.7, 0.6]  # 4 predicted positive (index 0,1,3,4), 1 predicted negative (index 2)
    # TP: indices 0, 1, 4 -> 3
    # FP: index 3 -> 1
    # TN: index 2 -> 1
    # FN: 0
    # Acc = 4/5 = 0.8
    # Prec = 3/4 = 0.75
    # Rec = 3/3 = 1.0
    # F1 = 2 * 0.75 * 1.0 / 1.75 = 0.8571

    res = calculate_classification_metrics(y_true=y_true, y_pred_prob=y_prob)
    assert res["status"] == "EVALUATED"
    metrics = res["metrics"]
    assert metrics["accuracy"] == 0.8
    assert metrics["precision"] == 0.75
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 0.8571
    assert metrics["brier_score"] is not None


def test_metrics_calculation_safe_on_zero_positives():
    """Zero positive cases in labels produces safe denominator without ZeroDivisionError."""
    y_true = [0, 0, 0]
    y_prob = [0.1, 0.2, 0.3]

    res = calculate_classification_metrics(y_true=y_true, y_pred_prob=y_prob)
    assert res["status"] == "EVALUATED"
    assert res["metrics"]["recall"] == 0.0
    assert "Dataset contains zero positive" in res["warning"]


# ==============================================================================
# 4. Model Interface & Agent Integration Tests
# ==============================================================================

def test_untrained_model_refuses_prediction():
    """An untrained model supplied to analyze_environment preserves UNVERIFIED fish presence."""
    untrained_model = DummyTrainedBiologicalModel(is_trained=False)
    evidence = EnvironmentalEvidence(
        wave_height_m=1.2,
        wave_observed_at=datetime(2026, 10, 13, tzinfo=timezone.utc),
        wave_source="Open-Meteo",
    )
    feature_vec = BiologicalFeatureVector(
        species_code="RAG",
        latitude=15.0,
        longitude=73.0,
        observed_at=datetime(2026, 10, 13, tzinfo=timezone.utc),
        sea_surface_temperature_c=28.0,
    )

    res = analyze_environment(
        evidence,
        model=untrained_model,
        feature_vector=feature_vec,
        now=datetime(2026, 10, 13, tzinfo=timezone.utc),
    )

    assert res["model_inference_status"] == "MODEL_NOT_TRAINED"
    assert res["fish_presence"] == "UNVERIFIED"
    assert res["catch_probability"] is None
    assert res["predictive_accuracy"] == "NOT_EVALUABLE"


def test_trained_model_inference_integrated_with_safeguards():
    """Trained model with valid features produces verified prediction output."""
    trained_model = DummyTrainedBiologicalModel(is_trained=True)
    evidence = EnvironmentalEvidence(
        wave_height_m=1.2,
        wave_observed_at=datetime(2026, 10, 13, tzinfo=timezone.utc),
        wave_source="Open-Meteo",
        sea_surface_temperature_c=28.5,
        sst_observed_at=datetime(2026, 10, 13, tzinfo=timezone.utc),
        sst_source="Open-Meteo Marine",
    )
    feature_vec = BiologicalFeatureVector(
        species_code="RAG",
        latitude=15.0,
        longitude=73.0,
        observed_at=datetime(2026, 10, 13, tzinfo=timezone.utc),
        sea_surface_temperature_c=28.5,
    )

    res = analyze_environment(
        evidence,
        model=trained_model,
        feature_vector=feature_vec,
        now=datetime(2026, 10, 13, tzinfo=timezone.utc),
    )

    assert res["model_inference_status"] == "INFERENCE_SUCCESS"
    assert res["fish_presence"] == "VERIFIED_PRESENT"
    assert res["catch_probability"] == 0.85
    assert res["target_species"] == "RAG"
    # Crucially: environmental completeness is 67% (wave + sst fresh out of 3), NOT 85%
    assert res["environmental_evidence_completeness_pct"] == 67
    assert res["score_type"] == "ENVIRONMENTAL_DATA_COMPLETENESS_ONLY"


def test_contract_violation_blocks_trained_model_inference():
    """Unphysical feature input (e.g. SST 60 C) blocks model inference."""
    trained_model = DummyTrainedBiologicalModel(is_trained=True)
    evidence = EnvironmentalEvidence()
    feature_vec = BiologicalFeatureVector(
        species_code="RAG",
        latitude=15.0,
        longitude=73.0,
        observed_at=datetime(2026, 10, 13, tzinfo=timezone.utc),
        sea_surface_temperature_c=60.0,  # Unphysical!
    )

    res = analyze_environment(
        evidence,
        model=trained_model,
        feature_vector=feature_vec,
        now=datetime(2026, 10, 13, tzinfo=timezone.utc),
    )

    assert res["model_inference_status"] == "FEATURE_CONTRACT_VIOLATION"
    assert res["fish_presence"] == "UNVERIFIED"
    assert any("unphysical_sst" in e for e in res["contract_validation_errors"])


def test_harness_evaluates_model_on_test_features():
    """BiologicalEvaluationHarness evaluates a trained model against ground truth labels."""
    harness = BiologicalEvaluationHarness()
    model = DummyTrainedBiologicalModel(is_trained=True)

    features = [
        BiologicalFeatureVector(
            species_code="RAG",
            latitude=15.0,
            longitude=73.0,
            observed_at=datetime(2026, 10, 12, tzinfo=timezone.utc),
            sea_surface_temperature_c=28.0,  # Predicted present
        ),
        BiologicalFeatureVector(
            species_code="RAG",
            latitude=15.0,
            longitude=73.0,
            observed_at=datetime(2026, 10, 12, tzinfo=timezone.utc),
            sea_surface_temperature_c=22.0,  # Predicted absent
        ),
    ]
    y_true = [1, 0]

    report = harness.evaluate_model(model, features, y_true)
    assert report["status"] == "EVALUATED"
    assert report["metrics"]["accuracy"] == 1.0
    assert report["metrics"]["f1_score"] == 1.0


# ==============================================================================
# 5. v3.6 Inference Contract Verification & Defect Hardening Tests
# ==============================================================================

class CrashingBiologicalModel(DummyTrainedBiologicalModel):
    """Model that raises an internal exception during inference."""

    def predict(self, features: BiologicalFeatureVector) -> BiologicalPredictionResult:
        raise RuntimeError("Internal numerical divergence in neural weights: Division by zero")


class OutOfBoundsProbabilityModel(DummyTrainedBiologicalModel):
    """Model that attempts to return probabilities outside [0, 1] or NaN."""

    def __init__(self, bad_prob: float) -> None:
        super().__init__(is_trained=True)
        self.bad_prob = bad_prob

    def predict(self, features: BiologicalFeatureVector) -> BiologicalPredictionResult:
        # Construct directly bypassing pydantic boundary to test system defense
        res = super().predict(features)
        # Force invalid probability attribute
        object.__setattr__(res, "probability", self.bad_prob)
        return res


class NegativeBiomassModel(DummyTrainedBiologicalModel):
    """Model that attempts to return unphysical negative biomass density."""

    def predict(self, features: BiologicalFeatureVector) -> BiologicalPredictionResult:
        res = super().predict(features)
        object.__setattr__(res, "biomass_density_kg_km2", -25.0)
        return res


class InvalidMetadataModel(DummyTrainedBiologicalModel):
    """Model that supplies empty or corrupt metadata."""

    def model_metadata(self) -> dict[str, Any]:
        return {}  # Missing model_id and version


def test_untrained_model_predict_method_never_called():
    """Verify that an untrained model's predict() is strictly never invoked."""
    class FailingUntrainedModel(BiologicalModelInterface):
        def is_trained(self) -> bool:
            return False

        def supported_species(self) -> list[str]:
            return ["RAG"]

        def model_metadata(self) -> dict[str, Any]:
            return {"model_id": "untrained", "version": "0.1"}

        def predict(self, features: BiologicalFeatureVector) -> BiologicalPredictionResult:
            raise AssertionError("CRITICAL FAILURE: predict() was called on an untrained model!")

        def predict_batch(self, features_list: list[BiologicalFeatureVector]) -> list[BiologicalPredictionResult]:
            raise AssertionError("CRITICAL FAILURE: predict_batch() was called on an untrained model!")

    untrained_model = FailingUntrainedModel()
    evidence = EnvironmentalEvidence()
    feature_vec = BiologicalFeatureVector(
        species_code="RAG",
        latitude=15.0,
        longitude=73.0,
        observed_at=datetime(2026, 10, 13, tzinfo=timezone.utc),
        sea_surface_temperature_c=28.0,
    )

    res = analyze_environment(
        evidence,
        model=untrained_model,
        feature_vector=feature_vec,
        now=datetime(2026, 10, 13, tzinfo=timezone.utc),
    )

    assert res["model_inference_status"] == "MODEL_NOT_TRAINED"
    assert res["fish_presence"] == "UNVERIFIED"


def test_model_exception_handled_safely_without_fabrication():
    """A model runtime exception never leaks or fabricates positive predictions."""
    crashing_model = CrashingBiologicalModel(is_trained=True)
    evidence = EnvironmentalEvidence()
    feature_vec = BiologicalFeatureVector(
        species_code="RAG",
        latitude=15.0,
        longitude=73.0,
        observed_at=datetime(2026, 10, 13, tzinfo=timezone.utc),
        sea_surface_temperature_c=28.0,
    )

    res = analyze_environment(
        evidence,
        model=crashing_model,
        feature_vector=feature_vec,
        now=datetime(2026, 10, 13, tzinfo=timezone.utc),
    )

    assert res["model_inference_status"] == "MODEL_EXECUTION_ERROR"
    assert "Division by zero" in res["model_execution_error"]
    assert res["fish_presence"] == "UNVERIFIED"
    assert res["catch_probability"] is None
    assert res["biomass_prediction"] is None


def test_probability_out_of_bounds_rejected_no_silent_clipping():
    """Predictions with probability > 1.0 or NaN are rejected, NOT silently clipped to 1.0."""
    bad_model = OutOfBoundsProbabilityModel(bad_prob=1.45)
    evidence = EnvironmentalEvidence()
    feature_vec = BiologicalFeatureVector(
        species_code="RAG",
        latitude=15.0,
        longitude=73.0,
        observed_at=datetime(2026, 10, 13, tzinfo=timezone.utc),
        sea_surface_temperature_c=28.0,
    )

    res = analyze_environment(
        evidence,
        model=bad_model,
        feature_vector=feature_vec,
        now=datetime(2026, 10, 13, tzinfo=timezone.utc),
    )

    assert res["model_inference_status"] == "INVALID_MODEL_OUTPUT"
    assert res["fish_presence"] == "UNVERIFIED"
    assert res["catch_probability"] is None  # Must NOT be clipped to 1.0
    assert any("invalid_probability" in err for err in res["output_validation_errors"])


def test_negative_biomass_rejected_no_silent_clipping():
    """Predictions with negative biomass are rejected, NOT silently clipped to 0.0."""
    bad_model = NegativeBiomassModel(is_trained=True)
    evidence = EnvironmentalEvidence()
    feature_vec = BiologicalFeatureVector(
        species_code="RAG",
        latitude=15.0,
        longitude=73.0,
        observed_at=datetime(2026, 10, 13, tzinfo=timezone.utc),
        sea_surface_temperature_c=28.0,
    )

    res = analyze_environment(
        evidence,
        model=bad_model,
        feature_vector=feature_vec,
        now=datetime(2026, 10, 13, tzinfo=timezone.utc),
    )

    assert res["model_inference_status"] == "INVALID_MODEL_OUTPUT"
    assert res["fish_presence"] == "UNVERIFIED"
    assert res["biomass_prediction"] is None  # Must NOT be clipped to 0.0
    assert any("invalid_biomass_density" in err for err in res["output_validation_errors"])


def test_model_metadata_validation_enforced():
    """Models with empty or invalid metadata dictionaries are rejected."""
    bad_meta_model = InvalidMetadataModel(is_trained=True)
    evidence = EnvironmentalEvidence()
    feature_vec = BiologicalFeatureVector(
        species_code="RAG",
        latitude=15.0,
        longitude=73.0,
        observed_at=datetime(2026, 10, 13, tzinfo=timezone.utc),
        sea_surface_temperature_c=28.0,
    )

    res = analyze_environment(
        evidence,
        model=bad_meta_model,
        feature_vector=feature_vec,
        now=datetime(2026, 10, 13, tzinfo=timezone.utc),
    )

    assert res["model_inference_status"] == "INVALID_MODEL_METADATA"
    assert res["fish_presence"] == "UNVERIFIED"


def test_species_compatibility_with_model_enforced():
    """Passing a species not supported by the model triggers rejection."""
    model = DummyTrainedBiologicalModel(is_trained=True)  # supports ["RAG", "RAK"]
    evidence = EnvironmentalEvidence()
    # YFT is a valid species in ORCA, but NOT supported by this mackerel-specific model
    feature_vec = BiologicalFeatureVector(
        species_code="YFT",
        latitude=15.0,
        longitude=73.0,
        observed_at=datetime(2026, 10, 13, tzinfo=timezone.utc),
        sea_surface_temperature_c=28.0,
    )

    res = analyze_environment(
        evidence,
        model=model,
        feature_vector=feature_vec,
        now=datetime(2026, 10, 13, tzinfo=timezone.utc),
    )

    assert res["model_inference_status"] == "UNSUPPORTED_SPECIES_FOR_MODEL"
    assert "YFT" in res["unsupported_species_error"]
    assert res["fish_presence"] == "UNVERIFIED"


def test_harness_unsupported_species_rejected_cleanly():
    """Harness rejects evaluation when test features target unsupported species."""
    harness = BiologicalEvaluationHarness()
    model = DummyTrainedBiologicalModel(is_trained=True)  # supports ["RAG", "RAK"]

    features = [
        BiologicalFeatureVector(
            species_code="YFT",  # Unsupported by model
            latitude=15.0,
            longitude=73.0,
            observed_at=datetime(2026, 10, 12, tzinfo=timezone.utc),
            sea_surface_temperature_c=28.0,
        )
    ]
    y_true = [1]

    report = harness.evaluate_model(model, features, y_true)
    assert report["status"] == "UNSUPPORTED_SPECIES_FOR_MODEL"
    assert report["metrics"] is None


def test_harness_unlabeled_data_returns_not_evaluable():
    """Harness returns NOT_EVALUABLE when all labels are None (unlabeled data)."""
    res = calculate_classification_metrics(y_true=[None, None, None], y_pred_prob=[0.8, 0.4, 0.2])
    assert res["status"] == "NOT_EVALUABLE"
    assert res["metrics"] is None
    assert "Zero verified ground-truth labels" in res["reason"]
