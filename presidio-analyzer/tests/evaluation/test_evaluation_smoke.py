"""End-to-end smoke run of the presidio-evaluator pipeline.

Skipped entirely when ``presidio-evaluator`` (the ``evaluation`` extra) is not
installed, so the general test matrix stays light. Floors are deliberately
loose: they catch a broken pipeline (no recognizers loaded, engine
misconfigured), not quality regressions.
"""

import json

import pytest

pytest.importorskip("presidio_evaluator")

from tests.evaluation.baseline import (  # noqa: E402
    default_baseline_path,
    load_baseline,
)
from tests.evaluation.evaluation import (  # noqa: E402
    default_dataset_path,
    run_evaluation,
)
from tests.evaluation.run_evaluation import main  # noqa: E402


@pytest.fixture(scope="module")
def entities():
    with open(default_dataset_path(), encoding="utf-8") as f:
        return json.load(f)["entities"]


@pytest.fixture(scope="module")
def n_samples():
    with open(default_dataset_path(), encoding="utf-8") as f:
        return len(json.load(f)["samples"])


@pytest.fixture(scope="module")
def report():
    return run_evaluation()


def test_metrics_are_reported_for_all_entities(report, entities, n_samples):
    assert set(report.per_entity) == set(entities)
    assert report.n_samples == n_samples


def test_detection_is_not_catastrophically_broken(report):
    assert report.overall_recall > 0.5, report.to_markdown()
    assert report.overall_precision > 0.5, report.to_markdown()


def test_structured_recognizers_detect_simple_cases(report):
    for entity in ("EMAIL_ADDRESS", "CREDIT_CARD", "IBAN_CODE", "US_SSN"):
        assert report.per_entity[entity].recall > 0.5, report.to_markdown()


def test_committed_baseline_covers_dataset_entities(entities):
    baseline = load_baseline(default_baseline_path())
    assert set(baseline["per_entity"]) == set(entities)


def test_cli_report_baseline_roundtrip_and_gating(tmp_path):
    # One flow to avoid repeated engine loads: write a fresh baseline, verify
    # self-comparison passes gating, then verify a doctored baseline trips
    # --fail-on-regression.
    baseline_path = tmp_path / "baseline.json"
    assert main(["--write-baseline", str(baseline_path)]) == 0

    report_path = tmp_path / "report.md"
    exit_code = main(
        [
            "--baseline", str(baseline_path),
            "--output", str(report_path),
            "--fail-on-regression",
        ]
    )
    assert exit_code == 0
    markdown = report_path.read_text(encoding="utf-8")
    assert "## Analyzer evaluation report" in markdown
    assert "F2 Δ |" in markdown

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline["overall"]["f2"] = 1.0
    doctored_path = tmp_path / "doctored.json"
    doctored_path.write_text(json.dumps(baseline), encoding="utf-8")

    exit_code = main(
        [
            "--baseline", str(doctored_path),
            "--output", str(report_path),
            "--fail-on-regression",
        ]
    )
    assert exit_code == 1
