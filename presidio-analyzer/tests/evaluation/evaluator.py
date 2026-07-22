"""Span-level evaluator for measuring analyzer detection quality.

The evaluator compares analyzer predictions against a hand-annotated golden
dataset and produces per-entity precision/recall/F1, latency figures and a
list of mismatches (false positives / false negatives) for human review.

Matching is span-based: a prediction matches a gold annotation when both have
the same entity type and their character ranges overlap with an
intersection-over-union (IoU) at or above a configurable threshold.
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from presidio_analyzer import RecognizerResult


@dataclass(frozen=True)
class GoldSpan:
    """A single annotated entity span in a golden dataset sample."""

    entity_type: str
    start: int
    end: int
    entity_value: str


@dataclass(frozen=True)
class EvaluationSample:
    """A single annotated text sample."""

    sample_id: str
    category: str
    text: str
    spans: List[GoldSpan]


@dataclass
class EntityMetrics:
    """Aggregated true/false positive/negative counts for one entity type."""

    entity_type: str
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    @property
    def support(self) -> int:
        """Number of gold annotations for this entity type."""
        return self.true_positives + self.false_negatives

    @property
    def precision(self) -> float:
        """Precision, or 0.0 when there are no predictions."""
        denominator = self.true_positives + self.false_positives
        return self.true_positives / denominator if denominator else 0.0

    @property
    def recall(self) -> float:
        """Recall, or 0.0 when there are no gold annotations."""
        denominator = self.true_positives + self.false_negatives
        return self.true_positives / denominator if denominator else 0.0

    @property
    def f1(self) -> float:
        """Harmonic mean of precision and recall."""
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * self.precision * self.recall / (self.precision + self.recall)


@dataclass(frozen=True)
class SpanMismatch:
    """A single false positive or false negative, kept for the report."""

    sample_id: str
    kind: str  # "false_positive" or "false_negative"
    entity_type: str
    span_text: str


@dataclass
class EvaluationResult:
    """Full result of an evaluation run."""

    per_entity: Dict[str, EntityMetrics]
    mismatches: List[SpanMismatch] = field(default_factory=list)
    n_samples: int = 0
    total_chars: int = 0
    total_seconds: float = 0.0

    @property
    def true_positives(self) -> int:
        """Total true positives across entity types."""
        return sum(m.true_positives for m in self.per_entity.values())

    @property
    def false_positives(self) -> int:
        """Total false positives across entity types."""
        return sum(m.false_positives for m in self.per_entity.values())

    @property
    def false_negatives(self) -> int:
        """Total false negatives across entity types."""
        return sum(m.false_negatives for m in self.per_entity.values())

    @property
    def precision(self) -> float:
        """Micro-averaged precision across entity types."""
        denominator = self.true_positives + self.false_positives
        return self.true_positives / denominator if denominator else 0.0

    @property
    def recall(self) -> float:
        """Micro-averaged recall across entity types."""
        denominator = self.true_positives + self.false_negatives
        return self.true_positives / denominator if denominator else 0.0

    @property
    def f1(self) -> float:
        """Micro-averaged F1 across entity types."""
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * self.precision * self.recall / (self.precision + self.recall)

    @property
    def chars_per_second(self) -> float:
        """Analyzer throughput over the whole dataset."""
        return self.total_chars / self.total_seconds if self.total_seconds else 0.0

    def to_markdown(
        self, max_mismatches: int = 25, baseline: Optional[Dict] = None
    ) -> str:
        """Render the result as a markdown report.

        :param max_mismatches: Cap on the number of mismatch rows included.
        :param baseline: Optional baseline dict (see ``baseline.py``); when
            given, an F1-delta column is added to the per-entity table.
        """
        overall_line = (
            f"**Overall (micro): precision {self.precision:.3f} | "
            f"recall {self.recall:.3f} | F1 {self.f1:.3f}"
        )
        if baseline:
            overall_delta = _round_delta(self.f1 - baseline["overall"]["f1"])
            overall_line += f" ({overall_delta:+.3f} vs baseline)"
        overall_line += "**"

        header = "| Entity | Support | TP | FP | FN | Precision | Recall | F1 |"
        separator = "|---|---|---|---|---|---|---|---|"
        if baseline:
            header += " F1 Δ |"
            separator += "---|"

        lines = [
            "## Analyzer evaluation report",
            "",
            f"Samples: {self.n_samples} | Characters: {self.total_chars} | "
            f"Throughput: {self.chars_per_second:,.0f} chars/sec | "
            f"Total analyze time: {self.total_seconds:.2f}s",
            "",
            overall_line,
            "",
            header,
            separator,
        ]
        for entity_type in sorted(self.per_entity):
            m = self.per_entity[entity_type]
            row = (
                f"| {m.entity_type} | {m.support} | {m.true_positives} "
                f"| {m.false_positives} | {m.false_negatives} "
                f"| {m.precision:.3f} | {m.recall:.3f} | {m.f1:.3f} |"
            )
            if baseline:
                baseline_entity = baseline["per_entity"].get(entity_type)
                if baseline_entity is None:
                    row += " new |"
                else:
                    row += f" {_round_delta(m.f1 - baseline_entity['f1']):+.3f} |"
            lines.append(row)

        if self.mismatches:
            lines += [
                "",
                f"### Mismatches (first {min(len(self.mismatches), max_mismatches)} "
                f"of {len(self.mismatches)})",
                "",
                "| Sample | Kind | Entity | Text |",
                "|---|---|---|---|",
            ]
            for mismatch in self.mismatches[:max_mismatches]:
                span_text = mismatch.span_text.replace("|", "\\|")
                lines.append(
                    f"| {mismatch.sample_id} | {mismatch.kind} "
                    f"| {mismatch.entity_type} | `{span_text}` |"
                )

        lines.append("")
        return "\n".join(lines)


def load_golden_dataset(path: Path) -> Dict:
    """Load a golden dataset file.

    :param path: Path to the dataset JSON file.
    :return: Dict with keys ``entities`` (evaluated entity types) and
        ``samples`` (list of :class:`EvaluationSample`).
    """
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    samples = [
        EvaluationSample(
            sample_id=sample["id"],
            category=sample["category"],
            text=sample["text"],
            spans=[
                GoldSpan(
                    entity_type=span["entity_type"],
                    start=span["start"],
                    end=span["end"],
                    entity_value=span["entity_value"],
                )
                for span in sample["spans"]
            ],
        )
        for sample in raw["samples"]
    ]
    return {
        "language": raw["language"],
        "entities": raw["entities"],
        "samples": samples,
    }


def _round_delta(delta: float) -> float:
    """Round a metric delta for display, normalizing negative zero."""
    return round(delta, 3) + 0.0


def _iou(start_a: int, end_a: int, start_b: int, end_b: int) -> float:
    """Character-level intersection-over-union of two half-open spans."""
    intersection = min(end_a, end_b) - max(start_a, start_b)
    if intersection <= 0:
        return 0.0
    union = max(end_a, end_b) - min(start_a, start_b)
    return intersection / union


class SpanEvaluator:
    """Match analyzer predictions against gold spans and aggregate metrics.

    :param entities: Entity types to evaluate. Predictions outside this set
        are ignored so that recognizers not covered by the dataset do not
        produce spurious false positives.
    :param iou_threshold: Minimum character-level IoU for a same-type
        prediction to count as a match. ``1.0`` means exact span matching.
    """

    def __init__(self, entities: List[str], iou_threshold: float = 0.5):
        if not 0.0 < iou_threshold <= 1.0:
            raise ValueError("iou_threshold must be in (0.0, 1.0]")
        self.entities = set(entities)
        self.iou_threshold = iou_threshold

    def evaluate(
        self,
        samples: List[EvaluationSample],
        analyze_fn: Callable[[str], List[RecognizerResult]],
        score_threshold: float = 0.0,
    ) -> EvaluationResult:
        """Run the analyzer over all samples and aggregate metrics.

        :param samples: Annotated samples to evaluate on.
        :param analyze_fn: Callable running the analyzer on a text. Kept as a
            callable (rather than an AnalyzerEngine) so unit tests can inject
            predictions and callers control engine configuration.
        :param score_threshold: Drop predictions below this confidence score.
        """
        result = EvaluationResult(
            per_entity={
                entity: EntityMetrics(entity_type=entity)
                for entity in sorted(self.entities)
            }
        )

        for sample in samples:
            start_time = time.perf_counter()
            predictions = analyze_fn(sample.text)
            result.total_seconds += time.perf_counter() - start_time
            result.n_samples += 1
            result.total_chars += len(sample.text)

            predictions = [
                p
                for p in predictions
                if p.entity_type in self.entities and p.score >= score_threshold
            ]
            self._match_sample(sample, predictions, result)

        return result

    def _match_sample(
        self,
        sample: EvaluationSample,
        predictions: List[RecognizerResult],
        result: EvaluationResult,
    ) -> None:
        """Greedily match predictions to gold spans by descending IoU."""
        candidate_pairs = []
        for gold_index, gold in enumerate(sample.spans):
            for pred_index, prediction in enumerate(predictions):
                if prediction.entity_type != gold.entity_type:
                    continue
                iou = _iou(gold.start, gold.end, prediction.start, prediction.end)
                if iou >= self.iou_threshold:
                    candidate_pairs.append((iou, gold_index, pred_index))

        matched_gold = set()
        matched_predictions = set()
        for _, gold_index, pred_index in sorted(
            candidate_pairs, key=lambda pair: -pair[0]
        ):
            if gold_index in matched_gold or pred_index in matched_predictions:
                continue
            matched_gold.add(gold_index)
            matched_predictions.add(pred_index)
            result.per_entity[sample.spans[gold_index].entity_type].true_positives += 1

        for gold_index, gold in enumerate(sample.spans):
            if gold_index not in matched_gold:
                result.per_entity[gold.entity_type].false_negatives += 1
                result.mismatches.append(
                    SpanMismatch(
                        sample_id=sample.sample_id,
                        kind="false_negative",
                        entity_type=gold.entity_type,
                        span_text=gold.entity_value,
                    )
                )

        for pred_index, prediction in enumerate(predictions):
            if pred_index not in matched_predictions:
                result.per_entity[prediction.entity_type].false_positives += 1
                result.mismatches.append(
                    SpanMismatch(
                        sample_id=sample.sample_id,
                        kind="false_positive",
                        entity_type=prediction.entity_type,
                        span_text=sample.text[prediction.start : prediction.end],
                    )
                )


def default_dataset_path() -> Path:
    """Path of the checked-in English golden dataset."""
    return Path(__file__).parent / "datasets" / "golden_en.json"
