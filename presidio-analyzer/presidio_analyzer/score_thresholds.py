"""Validation helpers for recognizer score thresholds."""

from collections.abc import Mapping
from typing import Dict

from presidio_analyzer._configuration_errors import ConfigValidationError


def validate_score_threshold(threshold: object) -> float:
    """Validate a score threshold without coercing its input type.

    :param threshold: The value to validate.
    :return: The validated score threshold.
    """
    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
        raise ConfigValidationError(
            f"Score threshold must be numeric, got: {threshold}",
            code="score_threshold",
            safe_message="Score threshold must be numeric (not boolean).",
        )
    if not 0.0 <= threshold <= 1.0:
        raise ConfigValidationError(
            f"Score threshold must be between 0.0 and 1.0, got: {threshold}",
            code="score_threshold",
            safe_message="Score threshold must be between 0.0 and 1.0.",
        )
    return threshold


def normalize_score_thresholds(score_thresholds: object) -> Dict[str, float]:
    """Validate and defensively copy one recognizer's score thresholds.

    :param score_thresholds: The threshold mapping to validate.
    :return: A normalized copy of the score thresholds.
    """
    if score_thresholds is None:
        return {}
    if not isinstance(score_thresholds, Mapping):
        raise ConfigValidationError(
            "score_thresholds must be a mapping",
            code="score_threshold",
            path=("score_thresholds",),
        )

    normalized = {}
    for entity, threshold in score_thresholds.items():
        if not isinstance(entity, str) or not entity or entity.strip() != entity:
            raise ConfigValidationError(
                "score_thresholds keys must be non-empty strings",
                code="score_threshold",
                path=("score_thresholds",),
            )
        try:
            normalized[entity] = validate_score_threshold(threshold)
        except ConfigValidationError as exc:
            raise ConfigValidationError(
                str(exc),
                code=exc.code,
                path=("score_thresholds", entity),
                safe_message=exc.safe_message,
            ) from exc
    return normalized
