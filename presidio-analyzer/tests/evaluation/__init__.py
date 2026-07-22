"""Span-level evaluation harness for the Presidio analyzer.

This package contains a curated golden dataset and a small evaluator that
measures per-entity precision/recall/F1 and latency for an analyzer
configuration. See tests/evaluation/README.md for the design and roadmap.
"""

from tests.evaluation.evaluator import (
    EntityMetrics,
    EvaluationResult,
    EvaluationSample,
    GoldSpan,
    SpanEvaluator,
    SpanMismatch,
    load_golden_dataset,
)

__all__ = [
    "EntityMetrics",
    "EvaluationResult",
    "EvaluationSample",
    "GoldSpan",
    "SpanEvaluator",
    "SpanMismatch",
    "load_golden_dataset",
]
