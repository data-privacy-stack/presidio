"""Unit tests for baseline persistence and regression comparison.

These tests build ``EvaluationReport``s directly and do not require
``presidio-evaluator`` to be installed.
"""

from tests.evaluation.baseline import (
    compare_to_baseline,
    load_baseline,
    report_to_baseline,
    save_baseline,
)
from tests.evaluation.evaluation import EntityScore, EvaluationReport


def _score(entity, tp, fp, fn, beta=2):
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    if precision + recall == 0:
        f2 = 0.0
    else:
        b2 = beta * beta
        f2 = (1 + b2) * precision * recall / (b2 * precision + recall)
    return EntityScore(
        entity_type=entity,
        support=tp + fn,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        precision=precision,
        recall=recall,
        f2=f2,
    )


def _report(per_entity_counts):
    """Build an EvaluationReport from {entity: (tp, fp, fn)}."""
    per_entity = {
        entity: _score(entity, tp, fp, fn)
        for entity, (tp, fp, fn) in per_entity_counts.items()
    }
    total_tp = sum(s.true_positives for s in per_entity.values())
    total_fp = sum(s.false_positives for s in per_entity.values())
    total_fn = sum(s.false_negatives for s in per_entity.values())
    precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0.0
    recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0.0
    f2 = 0.0 if precision + recall == 0 else 5 * precision * recall / (
        4 * precision + recall
    )
    return EvaluationReport(
        per_entity=per_entity,
        overall_precision=precision,
        overall_recall=recall,
        overall_f2=f2,
    )


class TestBaselineRoundTrip:
    def test_save_and_load(self, tmp_path):
        report = _report({"PERSON": (9, 1, 1), "EMAIL_ADDRESS": (5, 0, 0)})
        path = tmp_path / "baseline.json"

        save_baseline(report, config_name="test-config", path=path)
        baseline = load_baseline(path)

        assert baseline["config"] == "test-config"
        assert baseline["per_entity"]["PERSON"]["support"] == 10
        assert baseline["per_entity"]["EMAIL_ADDRESS"]["f2"] == 1.0
        assert baseline["overall"]["recall"] == round(report.overall_recall, 4)

    def test_report_matches_own_baseline(self):
        report = _report({"PERSON": (9, 1, 1)})
        baseline = report_to_baseline(report, config_name="test")

        assert compare_to_baseline(report, baseline) == []


class TestCompareToBaseline:
    def test_detects_per_entity_regression(self):
        good = _report({"PERSON": (10, 0, 0), "URL": (10, 0, 0)})
        baseline = report_to_baseline(good, config_name="test")
        regressed = _report({"PERSON": (10, 0, 0), "URL": (5, 5, 5)})

        regressions = compare_to_baseline(regressed, baseline)

        assert any("URL" in r for r in regressions)
        assert not any(r.startswith("PERSON") for r in regressions)

    def test_detects_overall_regression(self):
        good = _report({"PERSON": (10, 0, 0)})
        baseline = report_to_baseline(good, config_name="test")
        regressed = _report({"PERSON": (7, 3, 3)})

        regressions = compare_to_baseline(regressed, baseline)

        assert any(r.startswith("overall") for r in regressions)

    def test_drop_within_tolerance_is_not_a_regression(self):
        good = _report({"PERSON": (100, 0, 0)})
        baseline = report_to_baseline(good, config_name="test")
        slightly_worse = _report({"PERSON": (99, 0, 1)})

        assert compare_to_baseline(slightly_worse, baseline, f2_tolerance=0.02) == []

    def test_improvement_is_not_a_regression(self):
        weak = _report({"PERSON": (5, 5, 5)})
        baseline = report_to_baseline(weak, config_name="test")
        improved = _report({"PERSON": (10, 0, 0)})

        assert compare_to_baseline(improved, baseline) == []

    def test_entity_missing_from_baseline_is_skipped(self):
        # A weak new entity affects the overall micro average, but must not
        # produce a per-entity regression of its own.
        baseline = report_to_baseline(
            _report({"PERSON": (10, 0, 0)}), config_name="test"
        )
        with_new_entity = _report({"PERSON": (10, 0, 0), "UK_NHS": (0, 0, 5)})

        regressions = compare_to_baseline(with_new_entity, baseline)

        assert not any(r.startswith("UK_NHS") for r in regressions)
        assert any(r.startswith("overall") for r in regressions)


class TestMarkdownWithBaseline:
    def test_delta_column_present(self):
        report = _report({"PERSON": (10, 0, 0)})
        baseline = report_to_baseline(
            _report({"PERSON": (5, 5, 5)}), config_name="test"
        )

        markdown = report.to_markdown(baseline=baseline)

        assert "F2 Δ |" in markdown
        assert "vs baseline" in markdown

    def test_new_entity_marked_as_new(self):
        report = _report({"PERSON": (10, 0, 0), "UK_NHS": (3, 0, 0)})
        baseline = report_to_baseline(
            _report({"PERSON": (10, 0, 0)}), config_name="test"
        )

        markdown = report.to_markdown(baseline=baseline)

        assert "| UK_NHS | 3 | 3 | 0 | 0 | 1.000 | 1.000 | 1.000 | new |" in markdown

    def test_no_delta_column_without_baseline(self):
        report = _report({"PERSON": (10, 0, 0)})

        markdown = report.to_markdown()

        assert "F2 Δ" not in markdown
