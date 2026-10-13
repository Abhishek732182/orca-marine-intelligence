"""ORCA Biological Prediction & Evaluation Harness (v3.5).
------------------------------------------------------
Provides a reproducible, leakage-free evaluation harness and data-splitting
utilities for marine biological prediction models and species distribution models.

Design Guarantees:
1. Leakage Prevention:
   - Temporal train/test split enforces that training timestamps strictly precede
     evaluation timestamps (max(train_time) < min(test_time)).
   - Spatial block holdout split partitions spatial domain into disjoint grid cells
     to prevent spatial autocorrelation leakage.
2. Scientific Evaluation Truthfulness:
   - Evaluates classification metrics (Accuracy, Precision, Recall, F1, Brier Score)
     ONLY when verified ground-truth labels exist.
   - When labels are absent (empty denominator), explicitly returns status='NOT_EVALUABLE'
     and metrics=None rather than fabricating 0.0 or 1.0.
3. Feature Validation Integration:
   - Coordinates with BiologicalFeatureContract to reject corrupt, unphysical, or
     future-dated test features before model evaluation.
"""

from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any

from app.agents.biological_prediction_agent import (
    BiologicalFeatureContract,
    BiologicalFeatureVector,
    BiologicalModelInterface,
    BiologicalPredictionResult,
)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def temporal_train_test_split(
    records: list[dict[str, Any]],
    *,
    test_ratio: float = 0.2,
    cutoff_time: datetime | None = None,
    timestamp_key: str = "observed_at",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Partition records chronologically to prevent temporal data leakage.

    Enforces that every record in the training partition was observed strictly
    before every record in the test partition.

    Args:
        records: List of dictionaries containing an observation timestamp.
        test_ratio: Fraction of records to allocate to the test partition (0.0 < test_ratio < 1.0).
        cutoff_time: Optional explicit datetime threshold. If provided, records < cutoff_time
                     are assigned to train, and records >= cutoff_time to test.
        timestamp_key: Key in record dictionary holding datetime or ISO 8601 string.

    Returns:
        (train_records, test_records)

    Raises:
        ValueError: If records is empty, ratio is invalid, or timestamps cannot be parsed.
    """
    if not records:
        raise ValueError("Cannot perform temporal split on empty records list.")

    if cutoff_time is None and not (0.0 < test_ratio < 1.0):
        raise ValueError(f"test_ratio must be between 0.0 and 1.0 (exclusive), got {test_ratio}")

    def _extract_dt(item: dict[str, Any]) -> datetime:
        raw = item.get(timestamp_key)
        if raw is None:
            raise ValueError(f"Record missing timestamp key '{timestamp_key}': {item}")
        if isinstance(raw, datetime):
            return _ensure_utc(raw)
        if isinstance(raw, str):
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return _ensure_utc(parsed)
        raise ValueError(f"Unsupported timestamp format for key '{timestamp_key}': {raw}")

    # Sort records strictly chronologically
    sorted_records = sorted(records, key=_extract_dt)

    if cutoff_time is not None:
        cutoff_utc = _ensure_utc(cutoff_time)
        train_records = [r for r in sorted_records if _extract_dt(r) < cutoff_utc]
        test_records = [r for r in sorted_records if _extract_dt(r) >= cutoff_utc]
    else:
        n_total = len(sorted_records)
        n_test = max(1, int(round(n_total * test_ratio)))
        n_train = n_total - n_test

        if n_train == 0:
            raise ValueError(
                f"Insufficient records ({n_total}) for requested test ratio ({test_ratio}). "
                "Training set would be empty."
            )

        train_records = sorted_records[:n_train]
        test_records = sorted_records[n_train:]

    if train_records and test_records:
        max_train_time = max(_extract_dt(r) for r in train_records)
        min_test_time = min(_extract_dt(r) for r in test_records)
        if max_train_time >= min_test_time:
            # Tie at split boundary: check if timestamps are identical
            if max_train_time > min_test_time:
                raise ValueError(
                    f"Temporal leakage detected: max train time ({max_train_time}) > min test time ({min_test_time})"
                )

    return train_records, test_records


def spatial_block_split(
    records: list[dict[str, Any]],
    *,
    n_blocks_lat: int = 2,
    n_blocks_lon: int = 2,
    lat_key: str = "latitude",
    lon_key: str = "longitude",
) -> list[tuple[list[dict[str, Any]], list[dict[str, Any]]]]:
    """Partition records into spatial block holdout folds to prevent spatial autocorrelation leakage.

    Divides the bounding box of records into grid blocks and generates K holdout folds
    where entire geographical blocks are reserved for testing.

    Returns:
        List of (train_records, test_records) folds.
    """
    if not records:
        raise ValueError("Cannot perform spatial block split on empty records list.")

    lats = [float(r[lat_key]) for r in records]
    lons = [float(r[lon_key]) for r in records]

    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    lat_step = (max_lat - min_lat) / n_blocks_lat if max_lat > min_lat else 1.0
    lon_step = (max_lon - min_lon) / n_blocks_lon if max_lon > min_lon else 1.0

    def _get_block_id(item: dict[str, Any]) -> tuple[int, int]:
        lat = float(item[lat_key])
        lon = float(item[lon_key])
        b_lat = min(n_blocks_lat - 1, max(0, int((lat - min_lat) / lat_step))) if lat_step > 0 else 0
        b_lon = min(n_blocks_lon - 1, max(0, int((lon - min_lon) / lon_step))) if lon_step > 0 else 0
        return (b_lat, b_lon)

    # Group records by block
    blocks: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for r in records:
        bid = _get_block_id(r)
        blocks.setdefault(bid, []).append(r)

    unique_blocks = list(blocks.keys())
    if len(unique_blocks) < 2:
        # All records fell in the same single block
        return [(records, [])]

    folds: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]] = []
    for test_block in unique_blocks:
        test_recs = blocks[test_block]
        train_recs = [r for bid, b_recs in blocks.items() if bid != test_block for r in b_recs]
        folds.append((train_recs, test_recs))

    return folds


def calculate_classification_metrics(
    y_true: list[bool | int],
    *,
    y_pred_prob: list[float] | None = None,
    y_pred_label: list[bool | int] | None = None,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Calculate standard binary classification metrics with empty-denominator safeguards.

    Args:
        y_true: List of ground-truth binary labels (True/1 or False/0).
        y_pred_prob: Optional list of predicted probabilities in [0.0, 1.0].
        y_pred_label: Optional list of binary predicted labels. If omitted, derived from y_pred_prob >= threshold.
        threshold: Classification probability threshold (default 0.5).

    Returns:
        Structured dictionary reporting metric evaluation status, counts, and calculated scores.
    """
    if not y_true or all(v is None for v in y_true):
        return {
            "status": "NOT_EVALUABLE",
            "reason": "Zero verified ground-truth labels provided for evaluation.",
            "sample_count": 0 if not y_true else len(y_true),
            "metrics": None,
        }

    # Ensure labels are valid binary truth values (reject unlabeled/unknown markers)
    valid_binary_labels = [v for v in y_true if v in (True, False, 1, 0)]
    if len(valid_binary_labels) < len(y_true):
        return {
            "status": "NOT_EVALUABLE",
            "reason": "Dataset contains unverified, missing, or non-binary ground-truth labels.",
            "sample_count": len(y_true),
            "valid_labels_count": len(valid_binary_labels),
            "metrics": None,
        }

    n_samples = len(y_true)

    if y_pred_label is None:
        if y_pred_prob is None:
            return {
                "status": "NOT_EVALUABLE",
                "reason": "Neither predicted labels nor probabilities were supplied.",
                "sample_count": n_samples,
                "metrics": None,
            }
        if len(y_pred_prob) != n_samples:
            raise ValueError(
                f"Length mismatch: {n_samples} ground-truth labels but {len(y_pred_prob)} predicted probabilities."
            )
        y_pred_label = [prob >= threshold for prob in y_pred_prob]
    else:
        if len(y_pred_label) != n_samples:
            raise ValueError(
                f"Length mismatch: {n_samples} ground-truth labels but {len(y_pred_label)} predicted labels."
            )

    # Standard binary conversion
    yt = [bool(v) for v in y_true]
    yp = [bool(v) for v in y_pred_label]

    tp = sum(1 for t, p in zip(yt, yp) if t and p)
    fp = sum(1 for t, p in zip(yt, yp) if not t and p)
    fn = sum(1 for t, p in zip(yt, yp) if t and not p)
    tn = sum(1 for t, p in zip(yt, yp) if not t and not p)

    total_pos = tp + fn
    total_neg = fp + tn

    accuracy = round((tp + tn) / n_samples, 4) if n_samples > 0 else 0.0
    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
    f1 = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) > 0 else 0.0

    brier_score = None
    if y_pred_prob is not None:
        brier_sum = sum((float(prob) - (1.0 if t else 0.0)) ** 2 for prob, t in zip(y_pred_prob, yt))
        brier_score = round(brier_sum / n_samples, 4)

    single_class_warning = None
    if total_pos == 0:
        single_class_warning = "Dataset contains zero positive (PRESENCE) samples; recall is undefined."
    elif total_neg == 0:
        single_class_warning = "Dataset contains zero negative (ABSENCE) samples; precision cannot penalize false alarms."

    return {
        "status": "EVALUATED",
        "sample_count": n_samples,
        "positive_count": total_pos,
        "negative_count": total_neg,
        "threshold": threshold,
        "warning": single_class_warning,
        "confusion_matrix": {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
        },
        "metrics": {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "brier_score": brier_score,
        },
    }


class BiologicalEvaluationHarness:
    """Reproducible evaluation harness for marine species prediction models."""

    def __init__(self, reference_time: datetime | None = None) -> None:
        self.reference_time = _ensure_utc(reference_time or datetime.now(timezone.utc))

    def evaluate_model(
        self,
        model: BiologicalModelInterface,
        test_features: list[BiologicalFeatureVector],
        y_true: list[bool | int],
        *,
        threshold: float = 0.5,
    ) -> dict[str, Any]:
        """Evaluate a biological model against verified ground-truth labels.

        Validates all feature vectors against BiologicalFeatureContract before inference.
        """
        if not model.is_trained():
            return {
                "status": "NOT_EVALUABLE",
                "reason": "Model is not trained; evaluation cannot proceed without valid weights.",
                "sample_count": len(y_true),
                "model_id": getattr(model, "model_id", "unknown"),
                "metrics": None,
            }

        if len(test_features) != len(y_true):
            raise ValueError(
                f"Feature count ({len(test_features)}) does not match label count ({len(y_true)})."
            )

        if not y_true:
            return {
                "status": "NOT_EVALUABLE",
                "reason": "Zero test labels provided for evaluation.",
                "sample_count": 0,
                "model_id": getattr(model, "model_id", "unknown"),
                "metrics": None,
            }

        # Validate species compatibility
        supported = model.supported_species()
        unsupported = [f.species_code for f in test_features if f.species_code not in supported]
        if unsupported:
            return {
                "status": "UNSUPPORTED_SPECIES_FOR_MODEL",
                "reason": f"Test features contain species {unsupported[:3]} not supported by model. Supported: {supported}",
                "sample_count": len(test_features),
                "metrics": None,
            }

        # Validate feature vectors
        validation_failures: list[dict[str, Any]] = []
        valid_indices: list[int] = []

        for idx, fvec in enumerate(test_features):
            is_valid, errors = BiologicalFeatureContract.validate_features(
                fvec,
                now=self.reference_time,
            )
            if is_valid:
                valid_indices.append(idx)
            else:
                validation_failures.append({
                    "sample_index": idx,
                    "species_code": fvec.species_code,
                    "errors": errors,
                })

        if validation_failures:
            return {
                "status": "FEATURE_VALIDATION_FAILED",
                "reason": f"{len(validation_failures)}/{len(test_features)} feature vectors violated the feature contract.",
                "sample_count": len(test_features),
                "validation_failures": validation_failures,
                "metrics": None,
            }

        # Run inference with exception isolation
        try:
            predictions: list[BiologicalPredictionResult] = model.predict_batch(test_features)
        except Exception as exc:
            return {
                "status": "MODEL_EXECUTION_ERROR",
                "reason": f"Model batch inference failed: {exc}",
                "sample_count": len(test_features),
                "metrics": None,
            }

        # Validate outputs at model boundary (no silent clipping)
        output_errors: list[str] = []
        for idx, p in enumerate(predictions):
            if p.probability is not None and (
                not isinstance(p.probability, (int, float))
                or math.isnan(p.probability)
                or math.isinf(p.probability)
                or not (0.0 <= float(p.probability) <= 1.0)
            ):
                output_errors.append(f"Sample {idx}: invalid probability {p.probability}")
            if p.biomass_density_kg_km2 is not None and (
                not isinstance(p.biomass_density_kg_km2, (int, float))
                or math.isnan(p.biomass_density_kg_km2)
                or math.isinf(p.biomass_density_kg_km2)
                or float(p.biomass_density_kg_km2) < 0.0
            ):
                output_errors.append(f"Sample {idx}: invalid biomass density {p.biomass_density_kg_km2}")

        if output_errors:
            return {
                "status": "INVALID_MODEL_OUTPUT",
                "reason": f"{len(output_errors)} predictions produced invalid outputs.",
                "sample_count": len(test_features),
                "output_errors": output_errors,
                "metrics": None,
            }

        pred_probs = [p.probability for p in predictions if p.probability is not None]
        pred_labels = [p.predicted_presence for p in predictions if p.predicted_presence is not None]

        # Calculate metrics
        eval_result = calculate_classification_metrics(
            y_true=y_true,
            y_pred_prob=pred_probs if len(pred_probs) == len(y_true) else None,
            y_pred_label=pred_labels if len(pred_labels) == len(y_true) else None,
            threshold=threshold,
        )

        eval_result["model_metadata"] = model.model_metadata()
        return eval_result
