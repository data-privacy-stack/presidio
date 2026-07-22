"""Unit tests for the span evaluator (no NLP engine required)."""

import pytest

from presidio_analyzer import RecognizerResult
from tests.evaluation.evaluator import (
    EvaluationSample,
    GoldSpan,
    SpanEvaluator,
    _iou,
)


def _sample(sample_id, text, spans):
    return EvaluationSample(
        sample_id=sample_id, category="test", text=text, spans=spans
    )


def _gold(entity_type, start, end, text):
    return GoldSpan(
        entity_type=entity_type, start=start, end=end,
        entity_value=text[start:end],
    )


def _pred(entity_type, start, end, score=1.0):
    return RecognizerResult(
        entity_type=entity_type, start=start, end=end, score=score
    )


class TestIou:
    def test_identical_spans_have_iou_one(self):
        assert _iou(0, 10, 0, 10) == 1.0

    def test_disjoint_spans_have_iou_zero(self):
        assert _iou(0, 5, 5, 10) == 0.0

    def test_half_overlap(self):
        assert _iou(0, 10, 5, 15) == pytest.approx(5 / 15)


class TestSpanEvaluator:
    def test_invalid_iou_threshold_raises(self):
        with pytest.raises(ValueError):
            SpanEvaluator(entities=["PERSON"], iou_threshold=0.0)

    def test_exact_match_counts_as_true_positive(self):
        text = "My name is John Smith."
        sample = _sample("s1", text, [_gold("PERSON", 11, 21, text)])
        evaluator = SpanEvaluator(entities=["PERSON"])

        result = evaluator.evaluate([sample], lambda _: [_pred("PERSON", 11, 21)])

        metrics = result.per_entity["PERSON"]
        assert metrics.true_positives == 1
        assert metrics.false_positives == 0
        assert metrics.false_negatives == 0
        assert result.f1 == 1.0

    def test_missed_gold_span_is_false_negative(self):
        text = "My name is John Smith."
        sample = _sample("s1", text, [_gold("PERSON", 11, 21, text)])
        evaluator = SpanEvaluator(entities=["PERSON"])

        result = evaluator.evaluate([sample], lambda _: [])

        metrics = result.per_entity["PERSON"]
        assert metrics.false_negatives == 1
        assert result.recall == 0.0
        assert [m.kind for m in result.mismatches] == ["false_negative"]
        assert result.mismatches[0].span_text == "John Smith"

    def test_spurious_prediction_is_false_positive(self):
        text = "Nothing sensitive here at all."
        sample = _sample("s1", text, [])
        evaluator = SpanEvaluator(entities=["PERSON"])

        result = evaluator.evaluate([sample], lambda _: [_pred("PERSON", 0, 7)])

        metrics = result.per_entity["PERSON"]
        assert metrics.false_positives == 1
        assert result.precision == 0.0
        assert [m.kind for m in result.mismatches] == ["false_positive"]
        assert result.mismatches[0].span_text == "Nothing"

    def test_partial_overlap_above_threshold_matches(self):
        text = "Contact John Smith today."
        # Gold covers "John Smith", prediction covers only "John Smith toda"
        sample = _sample("s1", text, [_gold("PERSON", 8, 18, text)])
        evaluator = SpanEvaluator(entities=["PERSON"], iou_threshold=0.5)

        result = evaluator.evaluate([sample], lambda _: [_pred("PERSON", 8, 23)])

        assert result.per_entity["PERSON"].true_positives == 1

    def test_partial_overlap_below_threshold_does_not_match(self):
        text = "Contact John Smith today."
        sample = _sample("s1", text, [_gold("PERSON", 8, 18, text)])
        evaluator = SpanEvaluator(entities=["PERSON"], iou_threshold=0.9)

        result = evaluator.evaluate([sample], lambda _: [_pred("PERSON", 8, 23)])

        metrics = result.per_entity["PERSON"]
        assert metrics.true_positives == 0
        assert metrics.false_positives == 1
        assert metrics.false_negatives == 1

    def test_type_mismatch_does_not_match(self):
        text = "Reach me on 192.168.0.1 now."
        sample = _sample("s1", text, [_gold("IP_ADDRESS", 12, 23, text)])
        evaluator = SpanEvaluator(entities=["IP_ADDRESS", "PHONE_NUMBER"])

        result = evaluator.evaluate(
            [sample], lambda _: [_pred("PHONE_NUMBER", 12, 23)]
        )

        assert result.per_entity["IP_ADDRESS"].false_negatives == 1
        assert result.per_entity["PHONE_NUMBER"].false_positives == 1

    def test_predictions_outside_entity_set_are_ignored(self):
        text = "My name is John Smith."
        sample = _sample("s1", text, [_gold("PERSON", 11, 21, text)])
        evaluator = SpanEvaluator(entities=["PERSON"])

        result = evaluator.evaluate(
            [sample],
            lambda _: [_pred("PERSON", 11, 21), _pred("US_DRIVER_LICENSE", 0, 2)],
        )

        assert result.false_positives == 0
        assert "US_DRIVER_LICENSE" not in result.per_entity

    def test_predictions_below_score_threshold_are_dropped(self):
        text = "My name is John Smith."
        sample = _sample("s1", text, [_gold("PERSON", 11, 21, text)])
        evaluator = SpanEvaluator(entities=["PERSON"])

        result = evaluator.evaluate(
            [sample],
            lambda _: [_pred("PERSON", 11, 21, score=0.2)],
            score_threshold=0.5,
        )

        assert result.per_entity["PERSON"].false_negatives == 1

    def test_each_gold_span_matches_at_most_one_prediction(self):
        text = "Call John Smith or John Smith."
        sample = _sample("s1", text, [_gold("PERSON", 5, 15, text)])
        evaluator = SpanEvaluator(entities=["PERSON"])

        # Two identical predictions for one gold span: one TP, one FP.
        result = evaluator.evaluate(
            [sample], lambda _: [_pred("PERSON", 5, 15), _pred("PERSON", 5, 15)]
        )

        metrics = result.per_entity["PERSON"]
        assert metrics.true_positives == 1
        assert metrics.false_positives == 1

    def test_micro_average_over_multiple_samples(self):
        text_a = "Email a@b.com now."
        text_b = "Email c@d.org now."
        samples = [
            _sample("s1", text_a, [_gold("EMAIL_ADDRESS", 6, 13, text_a)]),
            _sample("s2", text_b, [_gold("EMAIL_ADDRESS", 6, 13, text_b)]),
        ]
        evaluator = SpanEvaluator(entities=["EMAIL_ADDRESS"])
        predictions = {
            text_a: [_pred("EMAIL_ADDRESS", 6, 13)],
            text_b: [],
        }

        result = evaluator.evaluate(samples, lambda text: predictions[text])

        assert result.n_samples == 2
        assert result.recall == 0.5
        assert result.precision == 1.0

    def test_markdown_report_contains_metrics_and_mismatches(self):
        text = "My name is John Smith."
        sample = _sample("s1", text, [_gold("PERSON", 11, 21, text)])
        evaluator = SpanEvaluator(entities=["PERSON"])

        result = evaluator.evaluate([sample], lambda _: [])
        report = result.to_markdown()

        assert "| PERSON | 1 | 0 | 0 | 1 |" in report
        assert "false_negative" in report
        assert "John Smith" in report
