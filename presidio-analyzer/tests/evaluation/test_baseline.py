"""Unit tests for baseline persistence and regression comparison."""

from tests.evaluation.baseline import (
    compare_to_baseline,
    load_baseline,
    result_to_baseline,
    save_baseline,
)
from tests.evaluation.evaluator import EntityMetrics, EvaluationResult


def _result(per_entity_counts):
    """Build an EvaluationResult from {entity: (tp, fp, fn)}."""
    return EvaluationResult(
        per_entity={
            entity: EntityMetrics(
                entity_type=entity,
                true_positives=tp,
                false_positives=fp,
                false_negatives=fn,
            )
            for entity, (tp, fp, fn) in per_entity_counts.items()
        }
    )


class TestBaselineRoundTrip:
    def test_save_and_load(self, tmp_path):
        result = _result({"PERSON": (9, 1, 1), "EMAIL_ADDRESS": (5, 0, 0)})
        path = tmp_path / "baseline.json"

        save_baseline(result, config_name="test-config", path=path)
        baseline = load_baseline(path)

        assert baseline["config"] == "test-config"
        assert baseline["per_entity"]["PERSON"]["support"] == 10
        assert baseline["per_entity"]["EMAIL_ADDRESS"]["f1"] == 1.0
        assert baseline["overall"]["recall"] == round(result.recall, 4)

    def test_result_matches_own_baseline(self):
        result = _result({"PERSON": (9, 1, 1)})
        baseline = result_to_baseline(result, config_name="test")

        assert compare_to_baseline(result, baseline) == []


class TestCompareToBaseline:
    def test_detects_per_entity_regression(self):
        good = _result({"PERSON": (10, 0, 0), "URL": (10, 0, 0)})
        baseline = result_to_baseline(good, config_name="test")
        regressed = _result({"PERSON": (10, 0, 0), "URL": (5, 5, 5)})

        regressions = compare_to_baseline(regressed, baseline)

        assert any("URL" in r for r in regressions)
        assert not any(r.startswith("PERSON") for r in regressions)

    def test_detects_overall_regression(self):
        good = _result({"PERSON": (10, 0, 0)})
        baseline = result_to_baseline(good, config_name="test")
        regressed = _result({"PERSON": (7, 3, 3)})

        regressions = compare_to_baseline(regressed, baseline)

        assert any(r.startswith("overall") for r in regressions)

    def test_drop_within_tolerance_is_not_a_regression(self):
        good = _result({"PERSON": (100, 0, 0)})
        baseline = result_to_baseline(good, config_name="test")
        slightly_worse = _result({"PERSON": (99, 0, 1)})

        assert compare_to_baseline(slightly_worse, baseline, f1_tolerance=0.02) == []

    def test_improvement_is_not_a_regression(self):
        weak = _result({"PERSON": (5, 5, 5)})
        baseline = result_to_baseline(weak, config_name="test")
        improved = _result({"PERSON": (10, 0, 0)})

        assert compare_to_baseline(improved, baseline) == []

    def test_entity_missing_from_baseline_is_skipped(self):
        # A weak new entity affects the overall micro average, but must not
        # produce a per-entity regression of its own.
        baseline = result_to_baseline(
            _result({"PERSON": (10, 0, 0)}), config_name="test"
        )
        with_new_entity = _result({"PERSON": (10, 0, 0), "UK_NHS": (0, 0, 5)})

        regressions = compare_to_baseline(with_new_entity, baseline)

        assert not any(r.startswith("UK_NHS") for r in regressions)
        assert any(r.startswith("overall") for r in regressions)


class TestMarkdownWithBaseline:
    def test_delta_column_present(self):
        result = _result({"PERSON": (10, 0, 0)})
        baseline = result_to_baseline(
            _result({"PERSON": (5, 5, 5)}), config_name="test"
        )

        report = result.to_markdown(baseline=baseline)

        assert "F1 Δ |" in report
        assert "+0.500 |" in report
        assert "vs baseline" in report

    def test_new_entity_marked_as_new(self):
        result = _result({"PERSON": (10, 0, 0), "UK_NHS": (3, 0, 0)})
        baseline = result_to_baseline(
            _result({"PERSON": (10, 0, 0)}), config_name="test"
        )

        report = result.to_markdown(baseline=baseline)

        assert "| UK_NHS | 3 | 3 | 0 | 0 | 1.000 | 1.000 | 1.000 | new |" in report

    def test_no_delta_column_without_baseline(self):
        result = _result({"PERSON": (10, 0, 0)})

        report = result.to_markdown()

        assert "F1 Δ" not in report
