"""Baseline persistence and regression comparison for evaluation reports.

A baseline is a checked-in snapshot of per-entity F2 metrics for one analyzer
configuration. Comparing a fresh report against it turns absolute numbers into
deltas and, when enforcement is switched on via ``--fail-on-regression``, lets
CI fail when F2 drops more than a tolerance below the baseline.

Throughput is deliberately not part of the baseline: it depends on the machine
running the evaluation and would make regressions non-reproducible.
"""

import json
from pathlib import Path
from typing import Dict, List

from tests.evaluation.evaluation import EvaluationReport

DEFAULT_F2_TOLERANCE = 0.02


def default_baseline_path() -> Path:
    """Path of the checked-in baseline for the default (spaCy) config."""
    return Path(__file__).parent / "baselines" / "spacy_en.json"


def report_to_baseline(report: EvaluationReport, config_name: str) -> Dict:
    """Snapshot an evaluation report as a baseline dict."""
    return {
        "config": config_name,
        "overall": {
            "precision": round(report.overall_precision, 4),
            "recall": round(report.overall_recall, 4),
            "f2": round(report.overall_f2, 4),
        },
        "per_entity": {
            entity: {
                "support": score.support,
                "precision": round(score.precision, 4),
                "recall": round(score.recall, 4),
                "f2": round(score.f2, 4),
            }
            for entity, score in sorted(report.per_entity.items())
        },
    }


def save_baseline(report: EvaluationReport, config_name: str, path: Path) -> None:
    """Write a baseline snapshot to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    baseline = report_to_baseline(report, config_name)
    path.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")


def load_baseline(path: Path) -> Dict:
    """Load a baseline snapshot from disk."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def compare_to_baseline(
    report: EvaluationReport,
    baseline: Dict,
    f2_tolerance: float = DEFAULT_F2_TOLERANCE,
) -> List[str]:
    """Compare a report against a baseline and describe regressions.

    :param report: Fresh evaluation report.
    :param baseline: Baseline dict, as produced by :func:`report_to_baseline`.
    :param f2_tolerance: Maximum allowed F2 drop before it counts as a
        regression, both overall and per entity type.
    :return: Human-readable regression descriptions; empty when the report
        is within tolerance. Entities absent from the baseline are skipped
        (they are new coverage, not regressions).
    """
    regressions = []

    overall_drop = baseline["overall"]["f2"] - report.overall_f2
    if overall_drop > f2_tolerance:
        regressions.append(
            f"overall F2 dropped {overall_drop:.3f} "
            f"(baseline {baseline['overall']['f2']:.3f}, "
            f"current {report.overall_f2:.3f}, tolerance {f2_tolerance})"
        )

    for entity, score in sorted(report.per_entity.items()):
        baseline_entity = baseline["per_entity"].get(entity)
        if baseline_entity is None:
            continue
        drop = baseline_entity["f2"] - score.f2
        if drop > f2_tolerance:
            regressions.append(
                f"{entity} F2 dropped {drop:.3f} "
                f"(baseline {baseline_entity['f2']:.3f}, "
                f"current {score.f2:.3f}, tolerance {f2_tolerance})"
            )

    return regressions
