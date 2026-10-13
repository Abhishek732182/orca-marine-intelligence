"""
ORCA Biological Prediction Agent
--------------------------------
Environmental suitability is a heuristic, NOT a biological prediction.

Fish presence, catch probability, biomass and accuracy remain unavailable
until authorized biological ground-truth data and a validated model exist.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import math
from typing import Any

from pydantic import BaseModel, Field, ConfigDict

from app.agents.species_rules import lookup_species


MAX_EVIDENCE_AGE_HOURS = 24


class EnvironmentalEvidence(BaseModel):
    """Environmental evidence supplied by verified data adapters."""

    model_config = ConfigDict(extra="forbid")

    wave_height_m: float | None = Field(default=None, ge=0, le=50)
    sea_surface_temperature_c: float | None = Field(
        default=None, ge=-5, le=50
    )
    chlorophyll_a_mg_m3: float | None = Field(
        default=None, ge=0, le=100
    )

    # Timestamp for each variable, in ISO 8601 format.
    wave_observed_at: datetime | None = None
    sst_observed_at: datetime | None = None
    chlorophyll_observed_at: datetime | None = None

    # These must come from the source adapter, not user self-assertion.
    wave_source: str | None = None
    sst_source: str | None = None
    chlorophyll_source: str | None = None


class BiologicalFeatureVector(BaseModel):
    """Normalized feature vector required for biological model inference."""

    model_config = ConfigDict(extra="forbid")

    species_code: str = Field(min_length=2, max_length=50)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    observed_at: datetime
    sea_surface_temperature_c: float | None = Field(default=None, ge=-50.0, le=100.0)
    chlorophyll_a_mg_m3: float | None = Field(default=None, ge=-10.0, le=500.0)
    salinity_psu: float | None = Field(default=None, ge=-5.0, le=100.0)
    bathymetry_depth_m: float | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BiologicalFeatureContract:
    """Enforces strict physical, biological, and temporal bounds on feature vectors."""

    MIN_SST_C = -2.0
    MAX_SST_C = 40.0
    MIN_CHLA = 0.0
    MAX_CHLA = 100.0

    @classmethod
    def validate_features(
        cls,
        features: BiologicalFeatureVector,
        *,
        required_features: list[str] | None = None,
        now: datetime | None = None,
    ) -> tuple[bool, list[str]]:
        """Validate feature vector against physical bounds, temporal freshness, and species registry.

        Returns:
            (is_valid, validation_errors)
        """
        errors: list[str] = []
        ref_time = _utc(now or datetime.now(timezone.utc))

        # 1. Species verification against documented registry
        lookup = lookup_species(features.species_code)
        if lookup.get("status") != "SUPPORTED":
            errors.append(
                f"unsupported_species: '{features.species_code}' is not recognized in SPECIES_REGISTRY"
            )

        # 2. Coordinate physical validity
        if math.isnan(features.latitude) or math.isinf(features.latitude) or not (-90.0 <= features.latitude <= 90.0):
            errors.append("invalid_latitude: must be finite number in [-90, 90]")
        if math.isnan(features.longitude) or math.isinf(features.longitude) or not (-180.0 <= features.longitude <= 180.0):
            errors.append("invalid_longitude: must be finite number in [-180, 180]")

        # 3. Temporal validity: no future-dated observations
        obs_utc = _utc(features.observed_at)
        if obs_utc > ref_time:
            errors.append(f"future_dated_observation: {obs_utc.isoformat()} is after reference time {ref_time.isoformat()}")

        # 4. Physical oceanographic boundaries
        if features.sea_surface_temperature_c is not None:
            if (
                math.isnan(features.sea_surface_temperature_c)
                or math.isinf(features.sea_surface_temperature_c)
                or not (cls.MIN_SST_C <= features.sea_surface_temperature_c <= cls.MAX_SST_C)
            ):
                errors.append(
                    f"unphysical_sst: {features.sea_surface_temperature_c}°C outside valid marine range [{cls.MIN_SST_C}, {cls.MAX_SST_C}]"
                )

        if features.chlorophyll_a_mg_m3 is not None:
            if (
                math.isnan(features.chlorophyll_a_mg_m3)
                or math.isinf(features.chlorophyll_a_mg_m3)
                or not (cls.MIN_CHLA <= features.chlorophyll_a_mg_m3 <= cls.MAX_CHLA)
            ):
                errors.append(
                    f"unphysical_chlorophyll: {features.chlorophyll_a_mg_m3} mg/m³ outside valid range [{cls.MIN_CHLA}, {cls.MAX_CHLA}]"
                )

        if features.salinity_psu is not None:
            if math.isnan(features.salinity_psu) or math.isinf(features.salinity_psu) or not (0.0 <= features.salinity_psu <= 45.0):
                errors.append(f"unphysical_salinity: {features.salinity_psu} PSU outside valid marine range [0, 45]")

        # 5. Required features check
        if required_features:
            for req in required_features:
                val = getattr(features, req, None)
                if val is None:
                    errors.append(f"missing_required_feature: '{req}' is required by model contract")

        return len(errors) == 0, errors


class BiologicalPredictionResult(BaseModel):
    """Standardized prediction output from an authorized biological model."""

    model_config = ConfigDict(extra="forbid")

    species_code: str
    target: str = Field(default="presence_absence")  # "presence_absence", "cpue_density", "catch_probability"
    predicted_presence: bool | None = None
    probability: float | None = Field(default=None, ge=0.0, le=1.0)
    biomass_density_kg_km2: float | None = Field(default=None, ge=0.0)
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    model_id: str
    model_version: str
    prediction_timestamp: datetime
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class BiologicalModelInterface(ABC):
    """Abstract base class defining the contract for biological prediction models."""

    @abstractmethod
    def predict(self, features: BiologicalFeatureVector) -> BiologicalPredictionResult:
        """Execute inference for a single validated feature vector."""
        pass

    @abstractmethod
    def predict_batch(
        self, features_list: list[BiologicalFeatureVector]
    ) -> list[BiologicalPredictionResult]:
        """Execute inference for a batch of validated feature vectors."""
        pass

    @abstractmethod
    def is_trained(self) -> bool:
        """Return True if model weights/parameters are loaded and validated."""
        pass

    @abstractmethod
    def supported_species(self) -> list[str]:
        """Return list of canonical species codes supported by this model."""
        pass

    @abstractmethod
    def model_metadata(self) -> dict[str, Any]:
        """Return model metadata, including training lineage, version, and metrics."""
        pass


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _fresh(value: datetime | None, now: datetime) -> bool:
    if value is None:
        return False

    age_hours = (_utc(now) - _utc(value)).total_seconds() / 3600

    # Future-dated evidence is not accepted.
    return 0 <= age_hours <= MAX_EVIDENCE_AGE_HOURS


def _evidence_status(
    value: float | None,
    timestamp: datetime | None,
    source: str | None,
    now: datetime,
) -> str:
    if value is None or timestamp is None or not source:
        return "UNAVAILABLE"

    if not _fresh(timestamp, now):
        return "STALE"

    return "FRESH"


def analyze_environment(
    evidence: EnvironmentalEvidence,
    *,
    model: BiologicalModelInterface | None = None,
    feature_vector: BiologicalFeatureVector | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """
    Return evidence quality, non-biological heuristic score, and optional model inference.

    Environmental completeness is strictly isolated: it reflects telemetry availability
    and does NOT estimate fish presence, catch probability, or biological biomass.
    """

    now = _utc(now or datetime.now(timezone.utc))

    variables = {
        "wave_height": _evidence_status(
            evidence.wave_height_m,
            evidence.wave_observed_at,
            evidence.wave_source,
            now,
        ),
        "sea_surface_temperature": _evidence_status(
            evidence.sea_surface_temperature_c,
            evidence.sst_observed_at,
            evidence.sst_source,
            now,
        ),
        "chlorophyll_a": _evidence_status(
            evidence.chlorophyll_a_mg_m3,
            evidence.chlorophyll_observed_at,
            evidence.chlorophyll_source,
            now,
        ),
    }

    fresh_count = sum(status == "FRESH" for status in variables.values())

    # Heuristic only: a simple indicator of environmental data availability.
    # It is NOT a fish habitat suitability or catch-probability score.
    environmental_evidence_completeness = round(
        100 * fresh_count / len(variables)
    )

    base_response: dict[str, Any] = {
        "agent": "ORCA Biological Prediction Agent",
        "status": (
            "ENVIRONMENTAL_EVIDENCE_AVAILABLE"
            if fresh_count
            else "INSUFFICIENT_FRESH_EVIDENCE"
        ),
        "environmental_evidence": variables,
        "fresh_variable_count": fresh_count,
        "environmental_evidence_completeness_pct": (
            environmental_evidence_completeness
        ),
        "score_type": "ENVIRONMENTAL_DATA_COMPLETENESS_ONLY",
        "fish_presence": "UNVERIFIED",
        "catch_probability": None,
        "biomass_prediction": None,
        "predictive_accuracy": "NOT_EVALUABLE",
        "ground_truth_status": "AWAITING_AUTHORIZED_DATA",
        "explanation": (
            "Environmental measurements alone do not establish fish "
            "presence, biomass or catch probability. A biological model "
            "must be trained and evaluated using authorized, suitable "
            "ground-truth observations."
        ),
        "safety_note": (
            "This output is not a fishing recommendation or vessel-safety "
            "clearance."
        ),
    }

    # If no biological model is supplied, preserve baseline safeguard invariants
    if model is None:
        return base_response

    # If model is supplied but not trained, refuse inference
    if not model.is_trained():
        base_response["model_inference_status"] = "MODEL_NOT_TRAINED"
        base_response["model_id"] = model.model_metadata().get("model_id", "unknown") if hasattr(model, "model_metadata") else "unknown"
        return base_response

    # Validate model metadata
    metadata = model.model_metadata()
    if not isinstance(metadata, dict) or not metadata.get("model_id") or not metadata.get("version"):
        base_response["model_inference_status"] = "INVALID_MODEL_METADATA"
        base_response["metadata_error"] = "Model metadata must be a non-empty dictionary containing 'model_id' and 'version'."
        return base_response

    model_id = metadata.get("model_id", "unknown")

    # If model is trained but feature vector is missing
    if feature_vector is None:
        base_response["model_inference_status"] = "MISSING_FEATURE_VECTOR"
        base_response["model_id"] = model_id
        return base_response

    # Validate feature vector against contract
    is_valid, validation_errors = BiologicalFeatureContract.validate_features(
        feature_vector,
        now=now,
    )
    if not is_valid:
        base_response["model_inference_status"] = "FEATURE_CONTRACT_VIOLATION"
        base_response["contract_validation_errors"] = validation_errors
        base_response["model_id"] = model_id
        return base_response

    # Validate species compatibility with model
    supported_species = model.supported_species()
    if not isinstance(supported_species, list) or feature_vector.species_code not in supported_species:
        base_response["model_inference_status"] = "UNSUPPORTED_SPECIES_FOR_MODEL"
        base_response["model_id"] = model_id
        base_response["unsupported_species_error"] = (
            f"Species '{feature_vector.species_code}' is not supported by model '{model_id}'. "
            f"Supported species: {supported_species}"
        )
        return base_response

    # Execute authorized inference with exception isolation
    try:
        prediction = model.predict(feature_vector)
    except Exception as exc:
        base_response["model_inference_status"] = "MODEL_EXECUTION_ERROR"
        base_response["model_id"] = model_id
        base_response["model_execution_error"] = str(exc)
        # Invariants preserved: never fabricate predictions upon model crash
        base_response["fish_presence"] = "UNVERIFIED"
        base_response["catch_probability"] = None
        base_response["biomass_prediction"] = None
        return base_response

    # Validate model outputs at boundary (DO NOT silently clip invalid predictions!)
    output_errors: list[str] = []
    if prediction.probability is not None:
        if (
            not isinstance(prediction.probability, (int, float))
            or math.isnan(prediction.probability)
            or math.isinf(prediction.probability)
            or not (0.0 <= float(prediction.probability) <= 1.0)
        ):
            output_errors.append(
                f"invalid_probability: {prediction.probability} is not a finite float in [0.0, 1.0]"
            )

    if prediction.biomass_density_kg_km2 is not None:
        if (
            not isinstance(prediction.biomass_density_kg_km2, (int, float))
            or math.isnan(prediction.biomass_density_kg_km2)
            or math.isinf(prediction.biomass_density_kg_km2)
            or float(prediction.biomass_density_kg_km2) < 0.0
        ):
            output_errors.append(
                f"invalid_biomass_density: {prediction.biomass_density_kg_km2} is not a finite non-negative float"
            )

    if prediction.confidence_score is not None:
        if (
            not isinstance(prediction.confidence_score, (int, float))
            or math.isnan(prediction.confidence_score)
            or math.isinf(prediction.confidence_score)
            or not (0.0 <= float(prediction.confidence_score) <= 1.0)
        ):
            output_errors.append(
                f"invalid_confidence_score: {prediction.confidence_score} is not a finite float in [0.0, 1.0]"
            )

    if output_errors:
        base_response["model_inference_status"] = "INVALID_MODEL_OUTPUT"
        base_response["model_id"] = model_id
        base_response["output_validation_errors"] = output_errors
        base_response["fish_presence"] = "UNVERIFIED"
        base_response["catch_probability"] = None
        base_response["biomass_prediction"] = None
        return base_response

    base_response["model_inference_status"] = "INFERENCE_SUCCESS"
    base_response["model_id"] = prediction.model_id
    base_response["model_version"] = prediction.model_version
    base_response["target_species"] = prediction.species_code
    base_response["fish_presence"] = "VERIFIED_PRESENT" if prediction.predicted_presence else "VERIFIED_ABSENT"
    base_response["catch_probability"] = prediction.probability
    base_response["biomass_prediction"] = prediction.biomass_density_kg_km2
    base_response["confidence_score"] = prediction.confidence_score
    base_response["model_diagnostics"] = prediction.diagnostics

    return base_response
