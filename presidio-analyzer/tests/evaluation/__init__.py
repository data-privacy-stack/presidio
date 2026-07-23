"""Analyzer detection-quality evaluation for CI.

A thin wrapper around ``presidio-evaluator`` that scores the analyzer against
a curated golden dataset and produces a per-entity precision/recall/F2 report
plus baseline regression comparison. See tests/evaluation/README.md.
"""

from tests.evaluation.evaluation import (
    EntityScore,
    EvaluationReport,
    Mismatch,
    default_dataset_path,
    load_input_samples,
    run_evaluation,
)

__all__ = [
    "EntityScore",
    "EvaluationReport",
    "Mismatch",
    "default_dataset_path",
    "load_input_samples",
    "run_evaluation",
]
