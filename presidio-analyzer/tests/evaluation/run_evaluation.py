"""Run the golden-dataset evaluation and emit a markdown report.

Usage (from the presidio-analyzer directory)::

    python -m tests.evaluation.run_evaluation [--output report.md] [--iou 0.5]

By default the evaluation runs the default AnalyzerEngine (spaCy NER plus
the predefined pattern recognizers) and, when the checked-in baseline for
that configuration exists, adds F1 deltas against it to the report.

Other analyzer configurations (e.g. transformers, GLiNER) can be evaluated
with ``--analyzer-conf <yaml>``; pair with ``--baseline`` / ``--write-baseline``
to track their metrics separately.

Regression enforcement exists but is off by default: pass
``--fail-on-regression`` to exit non-zero when overall or per-entity F1
drops more than ``--f1-tolerance`` below the baseline. CI currently runs
report-only; switching enforcement on is a one-line CI change once the
numbers have proven stable.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from tests.evaluation.baseline import (
    DEFAULT_F1_TOLERANCE,
    compare_to_baseline,
    default_baseline_path,
    load_baseline,
    save_baseline,
)
from tests.evaluation.evaluator import (
    EvaluationResult,
    SpanEvaluator,
    default_dataset_path,
    load_golden_dataset,
)

DEFAULT_CONFIG_NAME = "default (spacy en)"


def run_golden_evaluation(
    dataset_path: Optional[Path] = None,
    iou_threshold: float = 0.5,
    analyzer_conf: Optional[Path] = None,
) -> EvaluationResult:
    """Evaluate an analyzer configuration against the golden dataset.

    :param dataset_path: Dataset file; defaults to the checked-in golden set.
    :param iou_threshold: Span-overlap threshold passed to the evaluator.
    :param analyzer_conf: Optional full analyzer YAML configuration; when
        omitted, the default AnalyzerEngine is used.
    """
    from presidio_analyzer import AnalyzerEngine, AnalyzerEngineProvider

    dataset = load_golden_dataset(dataset_path or default_dataset_path())
    if analyzer_conf:
        engine = AnalyzerEngineProvider(
            analyzer_engine_conf_file=analyzer_conf
        ).create_engine()
    else:
        engine = AnalyzerEngine()
    language = dataset["language"]

    # Warm up so model load time is not attributed to the first sample.
    engine.analyze(text="warm up", language=language)

    evaluator = SpanEvaluator(
        entities=dataset["entities"], iou_threshold=iou_threshold
    )
    return evaluator.evaluate(
        samples=dataset["samples"],
        analyze_fn=lambda text: engine.analyze(text=text, language=language),
    )


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Path to a golden dataset JSON (default: bundled golden_en.json)",
    )
    parser.add_argument(
        "--analyzer-conf",
        type=Path,
        default=None,
        help="Full analyzer YAML configuration to evaluate "
        "(default: the default AnalyzerEngine)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="File to write the markdown report to (default: stdout)",
    )
    parser.add_argument(
        "--iou",
        type=float,
        default=0.5,
        help="Character IoU threshold for span matching (default: 0.5)",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="Baseline JSON to compare against (default: the checked-in "
        "spaCy baseline when evaluating the default configuration)",
    )
    parser.add_argument(
        "--write-baseline",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write the run's metrics as a new baseline to PATH and exit",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit non-zero when F1 drops below the baseline by more than "
        "the tolerance (off by default; CI runs report-only)",
    )
    parser.add_argument(
        "--f1-tolerance",
        type=float,
        default=DEFAULT_F1_TOLERANCE,
        help=f"Allowed F1 drop before a regression is reported "
        f"(default: {DEFAULT_F1_TOLERANCE})",
    )
    args = parser.parse_args(argv)

    result = run_golden_evaluation(
        dataset_path=args.dataset,
        iou_threshold=args.iou,
        analyzer_conf=args.analyzer_conf,
    )

    config_name = (
        str(args.analyzer_conf) if args.analyzer_conf else DEFAULT_CONFIG_NAME
    )
    if args.write_baseline:
        save_baseline(result, config_name=config_name, path=args.write_baseline)
        print(f"wrote baseline to {args.write_baseline}")
        return 0

    baseline = None
    baseline_path = args.baseline
    if baseline_path is None and args.analyzer_conf is None:
        default_path = default_baseline_path()
        if default_path.exists():
            baseline_path = default_path
    if baseline_path:
        baseline = load_baseline(baseline_path)

    report = result.to_markdown(baseline=baseline)
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        sys.stdout.write(report)

    if baseline:
        regressions = compare_to_baseline(
            result, baseline, f1_tolerance=args.f1_tolerance
        )
        if regressions:
            for regression in regressions:
                print(f"REGRESSION: {regression}", file=sys.stderr)
            if args.fail_on_regression:
                return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
