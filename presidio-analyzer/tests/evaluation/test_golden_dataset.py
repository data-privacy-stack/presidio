"""Integrity checks for the golden dataset, plus a report-only smoke run.

The smoke test intentionally asserts only a low floor: this phase is about
producing a trustworthy report, not gating on metrics. Regression gating
against checked-in baselines is a follow-up phase (see README.md).
"""

import json

import pytest

from tests.evaluation.baseline import default_baseline_path, load_baseline
from tests.evaluation.evaluator import default_dataset_path, load_golden_dataset
from tests.evaluation.generate_golden_en import build_dataset, dataset_to_json
from tests.evaluation.run_evaluation import main, run_golden_evaluation


@pytest.fixture(scope="module")
def dataset():
    return load_golden_dataset(default_dataset_path())


@pytest.fixture(scope="module")
def result():
    return run_golden_evaluation()


class TestDatasetIntegrity:
    def test_dataset_matches_generator(self):
        # The JSON file is generated, never hand-edited; regenerate with
        # `python -m tests.evaluation.generate_golden_en` after changing
        # the sample definitions.
        committed = default_dataset_path().read_text(encoding="utf-8")
        assert committed == dataset_to_json(build_dataset()), (
            "datasets/golden_en.json is out of sync with "
            "generate_golden_en.py; regenerate it with "
            "`python -m tests.evaluation.generate_golden_en`"
        )

    def test_sample_ids_are_unique(self, dataset):
        ids = [sample.sample_id for sample in dataset["samples"]]
        assert len(ids) == len(set(ids))

    def test_spans_match_text_offsets(self, dataset):
        for sample in dataset["samples"]:
            for span in sample.spans:
                assert sample.text[span.start : span.end] == span.entity_value, (
                    f"{sample.sample_id}: span [{span.start}:{span.end}] is "
                    f"{sample.text[span.start:span.end]!r}, "
                    f"expected {span.entity_value!r}"
                )

    def test_span_entity_types_are_declared(self, dataset):
        declared = set(dataset["entities"])
        for sample in dataset["samples"]:
            for span in sample.spans:
                assert span.entity_type in declared, (
                    f"{sample.sample_id}: {span.entity_type} missing from "
                    f"the dataset's declared entity list"
                )

    def test_every_declared_entity_has_gold_spans(self, dataset):
        annotated = {
            span.entity_type
            for sample in dataset["samples"]
            for span in sample.spans
        }
        assert annotated == set(dataset["entities"])

    def test_negative_samples_have_no_spans(self, dataset):
        for sample in dataset["samples"]:
            if sample.category == "negative":
                assert sample.spans == []


class TestGoldenEvaluationSmoke:
    """Run the default engine over the golden set (report-only floors)."""

    def test_metrics_are_reported_for_all_entities(self, result, dataset):
        assert set(result.per_entity) == set(dataset["entities"])
        assert result.n_samples == len(dataset["samples"])

    def test_detection_is_not_catastrophically_broken(self, result):
        # Deliberately loose floors: they only catch a broken pipeline
        # (e.g. no recognizers loaded), not quality regressions.
        assert result.recall > 0.5, result.to_markdown()
        assert result.precision > 0.5, result.to_markdown()

    def test_structured_recognizers_detect_simple_cases(self, result):
        # Pattern-based recognizers with validation should not miss
        # their clean, well-formatted golden examples entirely.
        for entity in ("EMAIL_ADDRESS", "CREDIT_CARD", "IBAN_CODE", "US_SSN"):
            assert result.per_entity[entity].recall > 0.5, result.to_markdown()

    def test_committed_baseline_covers_dataset_entities(self, dataset):
        baseline = load_baseline(default_baseline_path())
        assert set(baseline["per_entity"]) == set(dataset["entities"])

    def test_cli_report_baseline_roundtrip_and_gating(self, tmp_path):
        # One flow to avoid repeated engine loads: write a fresh baseline,
        # verify self-comparison passes gating, then verify a doctored
        # baseline trips --fail-on-regression.
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
        report = report_path.read_text(encoding="utf-8")
        assert "## Analyzer evaluation report" in report
        assert "F1 Δ |" in report

        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        baseline["overall"]["f1"] = 1.0
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
