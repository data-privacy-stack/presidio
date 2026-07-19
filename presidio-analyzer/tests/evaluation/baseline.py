"""Baseline persistence and regression comparison for evaluation results.

A baseline is a checked-in snapshot of per-entity metrics for one analyzer
configuration. Comparing a fresh evaluation against it turns the report's
absolute numbers into deltas, and — once enforcement is switched on via
``--fail-on-regression`` — lets CI fail when an entity's F1 drops by more
than a tolerance.

Throughput is deliberately not part of the baseline: it depends on the
machine running the evaluation and would make regressions non-reproducible.
"""

import json
from pathlib import Path
from typing import Dict, List

from tests.evaluation.evaluator import EvaluationResult

DEFAULT_F1_TOLERANCE = 0.02


def default_baseline_path() -> Path:
    """Path of the checked-in baseline for the default (spaCy) config."""
    return Path(__file__).parent / "baselines" / "spacy_en.json"


def result_to_baseline(result: EvaluationResult, config_name: str) -> Dict:
    """Snapshot an evaluation result as a baseline dict."""
    return {
        "config": config_name,
        "overall": {
            "precision": round(result.precision, 4),
            "recall": round(result.recall, 4),
            "f1": round(result.f1, 4),
        },
        "per_entity": {
            entity: {
                "support": metrics.support,
                "precision": round(metrics.precision, 4),
                "recall": round(metrics.recall, 4),
                "f1": round(metrics.f1, 4),
            }
            for entity, metrics in sorted(result.per_entity.items())
        },
    }


def save_baseline(result: EvaluationResult, config_name: str, path: Path) -> None:
    """Write a baseline snapshot to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    baseline = result_to_baseline(result, config_name)
    path.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")


def load_baseline(path: Path) -> Dict:
    """Load a baseline snapshot from disk."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def compare_to_baseline(
    result: EvaluationResult,
    baseline: Dict,
    f1_tolerance: float = DEFAULT_F1_TOLERANCE,
) -> List[str]:
    """Compare a result against a baseline and describe regressions.

    :param result: Fresh evaluation result.
    :param baseline: Baseline dict, as produced by :func:`result_to_baseline`.
    :param f1_tolerance: Maximum allowed F1 drop before it counts as a
        regression, both overall and per entity type.
    :return: Human-readable regression descriptions; empty when the result
        is within tolerance. Entities absent from the baseline are skipped
        (they are new coverage, not regressions).
    """
    regressions = []

    overall_drop = baseline["overall"]["f1"] - result.f1
    if overall_drop > f1_tolerance:
        regressions.append(
            f"overall F1 dropped {overall_drop:.3f} "
            f"(baseline {baseline['overall']['f1']:.3f}, "
            f"current {result.f1:.3f}, tolerance {f1_tolerance})"
        )

    for entity, metrics in sorted(result.per_entity.items()):
        baseline_entity = baseline["per_entity"].get(entity)
        if baseline_entity is None:
            continue
        drop = baseline_entity["f1"] - metrics.f1
        if drop > f1_tolerance:
            regressions.append(
                f"{entity} F1 dropped {drop:.3f} "
                f"(baseline {baseline_entity['f1']:.3f}, "
                f"current {metrics.f1:.3f}, tolerance {f1_tolerance})"
            )

    return regressions
