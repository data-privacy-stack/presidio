"""Analyzer evaluation on top of ``presidio-evaluator``.

This module is a thin CI-oriented wrapper around the org's
``presidio-evaluator`` package (``data-privacy-stack/presidio-research``). It
converts the checked-in golden dataset into ``InputSample``s, runs the
analyzer through ``PresidioAnalyzerWrapper`` + ``SpanEvaluator``, and reduces
the result to a small, serializable report used for the per-PR CI summary and
baseline comparison.

Scoring is span-based (character IoU) with F-beta = 2 (recall-weighted),
matching Presidio's documented evaluation convention. The ``CanonicalMapper``
entity-hierarchy step is intentionally skipped: the golden dataset is
annotated with the analyzer's own entity names, so predictions and
annotations already share a label space and no mapping is required.
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class EntityScore:
    """Per-entity metrics for one entity type (F-beta = 2)."""

    entity_type: str
    support: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f2: float = 0.0


@dataclass
class Mismatch:
    """A single false positive / false negative / wrong-entity error."""

    kind: str  # "false_positive" | "false_negative" | "wrong_entity"
    entity_type: str
    text: str


@dataclass
class EvaluationReport:
    """Reduced, serializable result of an evaluation run."""

    per_entity: Dict[str, EntityScore]
    overall_precision: float = 0.0
    overall_recall: float = 0.0
    overall_f2: float = 0.0
    n_samples: int = 0
    total_chars: int = 0
    total_seconds: float = 0.0
    mismatches: List[Mismatch] = field(default_factory=list)

    @property
    def chars_per_second(self) -> float:
        """Analyzer throughput over the whole dataset."""
        return self.total_chars / self.total_seconds if self.total_seconds else 0.0

    def to_markdown(
        self, max_mismatches: int = 25, baseline: Optional[Dict] = None
    ) -> str:
        """Render the report as markdown.

        :param max_mismatches: Cap on the number of mismatch rows included.
        :param baseline: Optional baseline dict (see ``baseline.py``); when
            given, an F2-delta column is added to the per-entity table.
        """
        overall = (
            f"**Overall (PII): precision {self.overall_precision:.3f} | "
            f"recall {self.overall_recall:.3f} | F2 {self.overall_f2:.3f}"
        )
        if baseline:
            overall += (
                f" ({_round_delta(self.overall_f2 - baseline['overall']['f2']):+.3f}"
                " vs baseline)"
            )
        overall += "**"

        header = "| Entity | Support | TP | FP | FN | Precision | Recall | F2 |"
        separator = "|---|---|---|---|---|---|---|---|"
        if baseline:
            header += " F2 Δ |"
            separator += "---|"

        lines = [
            "## Analyzer evaluation report",
            "",
            "Engine: `presidio-evaluator` SpanEvaluator (char IoU, β=2)",
            "",
            f"Samples: {self.n_samples} | Characters: {self.total_chars} | "
            f"Throughput: {self.chars_per_second:,.0f} chars/sec | "
            f"Total analyze time: {self.total_seconds:.2f}s",
            "",
            overall,
            "",
            header,
            separator,
        ]
        for entity_type in sorted(self.per_entity):
            m = self.per_entity[entity_type]
            row = (
                f"| {m.entity_type} | {m.support} | {m.true_positives} "
                f"| {m.false_positives} | {m.false_negatives} "
                f"| {m.precision:.3f} | {m.recall:.3f} | {m.f2:.3f} |"
            )
            if baseline:
                baseline_entity = baseline["per_entity"].get(entity_type)
                if baseline_entity is None:
                    row += " new |"
                else:
                    row += f" {_round_delta(m.f2 - baseline_entity['f2']):+.3f} |"
            lines.append(row)

        if self.mismatches:
            shown = min(len(self.mismatches), max_mismatches)
            lines += [
                "",
                f"### Mismatches (first {shown} of {len(self.mismatches)})",
                "",
                "| Kind | Entity | Text |",
                "|---|---|---|",
            ]
            for mismatch in self.mismatches[:max_mismatches]:
                text = mismatch.text.replace("|", "\\|").replace("\n", " ")
                lines.append(f"| {mismatch.kind} | {mismatch.entity_type} | `{text}` |")

        lines.append("")
        return "\n".join(lines)


def _round_delta(delta: float) -> float:
    """Round a metric delta for display, normalizing negative zero."""
    return round(delta, 3) + 0.0


def load_input_samples(path: Path):
    """Load the golden dataset as ``presidio_evaluator.InputSample``s.

    :param path: Path to a golden dataset JSON file.
    :return: Dict with ``language``, ``entities`` and ``samples``
        (a list of ``InputSample``).
    """
    from presidio_evaluator import InputSample, Span

    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    samples = []
    for sample in raw["samples"]:
        spans = [
            Span(
                entity_type=span["entity_type"],
                entity_value=span["entity_value"],
                start_position=span["start"],
                end_position=span["end"],
            )
            for span in sample["spans"]
        ]
        samples.append(
            InputSample(
                full_text=sample["text"],
                spans=spans,
                create_tags_from_span=True,
                metadata={"category": sample["category"], "id": sample["id"]},
            )
        )
    return {
        "language": raw["language"],
        "entities": raw["entities"],
        "samples": samples,
    }


_ERROR_KIND = {
    "FP": "false_positive",
    "FN": "false_negative",
    "WrongEntity": "wrong_entity",
}


def _build_report(evaluation_result, entities, n_samples, total_chars, elapsed):
    """Reduce a presidio-evaluator ``EvaluationResult`` to ``EvaluationReport``."""
    per_entity = {entity: EntityScore(entity_type=entity) for entity in entities}
    for entity, metrics in (evaluation_result.per_type or {}).items():
        per_entity[entity] = EntityScore(
            entity_type=entity,
            support=int(metrics.num_annotated),
            true_positives=int(metrics.true_positives),
            false_positives=int(metrics.false_positives),
            false_negatives=int(metrics.false_negatives),
            precision=float(metrics.precision),
            recall=float(metrics.recall),
            f2=float(metrics.f_beta),
        )

    mismatches = []
    for error in evaluation_result.model_errors or []:
        error_type = getattr(error.error_type, "value", str(error.error_type))
        entity = error.annotation if error_type == "FN" else error.prediction
        mismatches.append(
            Mismatch(
                kind=_ERROR_KIND.get(error_type, error_type),
                entity_type=entity,
                text=str(error.token),
            )
        )

    return EvaluationReport(
        per_entity=per_entity,
        overall_precision=float(evaluation_result.pii_precision or 0.0),
        overall_recall=float(evaluation_result.pii_recall or 0.0),
        overall_f2=float(evaluation_result.pii_f or 0.0),
        n_samples=n_samples,
        total_chars=total_chars,
        total_seconds=elapsed,
        mismatches=mismatches,
    )


def run_evaluation(
    dataset_path: Optional[Path] = None,
    iou_threshold: float = 0.5,
    analyzer_conf: Optional[Path] = None,
    score_threshold: float = 0.4,
) -> EvaluationReport:
    """Evaluate an analyzer configuration against the golden dataset.

    :param dataset_path: Dataset file; defaults to the checked-in golden set.
    :param iou_threshold: Character IoU threshold for span matching.
    :param analyzer_conf: Optional full analyzer YAML configuration; when
        omitted, the default AnalyzerEngine is used.
    :param score_threshold: Minimum analyzer confidence to keep a prediction.
    """
    from presidio_analyzer import (
        AnalyzerEngine,
        AnalyzerEngineProvider,
    )
    from presidio_evaluator.evaluation import SpanEvaluator
    from presidio_evaluator.models import PresidioAnalyzerWrapper

    dataset = load_input_samples(dataset_path or default_dataset_path())
    samples = dataset["samples"]
    entities = dataset["entities"]

    if analyzer_conf:
        engine = AnalyzerEngineProvider(
            analyzer_engine_conf_file=analyzer_conf
        ).create_engine()
    else:
        engine = AnalyzerEngine()

    wrapper = PresidioAnalyzerWrapper(
        analyzer_engine=engine,
        entities_to_keep=entities,
        language=dataset["language"],
        score_threshold=score_threshold,
    )

    start = time.perf_counter()
    results_df = wrapper.predict_dataset(samples)
    elapsed = time.perf_counter() - start

    evaluator = SpanEvaluator(iou_threshold=iou_threshold, entities_to_keep=entities)
    evaluation_result = evaluator.calculate_score_on_df(results_df, beta=2)

    total_chars = sum(len(sample.full_text) for sample in samples)
    return _build_report(
        evaluation_result, entities, len(samples), total_chars, elapsed
    )


def default_dataset_path() -> Path:
    """Path of the checked-in English golden dataset."""
    return Path(__file__).parent / "datasets" / "golden_en.json"
