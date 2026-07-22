import logging
from typing import Any, Dict, Iterable, Iterator, List, Optional

import spacy
from spacy.language import Language
from spacy.pipeline import Pipe
from spacy.tokens import Doc, Span, SpanGroup

try:
    from transformers import pipeline as hf_pipeline
except ImportError:
    hf_pipeline = None

from presidio_analyzer.nlp_engine import (
    NerModelConfiguration,
    SpacyNlpEngine,
    device_detector,
)

logger = logging.getLogger("presidio-analyzer")

_PIPE_NAME = "presidio_transformers_ner"


@Language.factory(
    _PIPE_NAME,
    assigns=[],
    default_config={
        "model": "",
        "stride": 14,
        "aggregation_strategy": "max",
        "alignment_mode": "expand",
        "spans_key": "bert-base-ner",
    },
)
def _create_transformers_ner_pipe(
    nlp: Language,
    name: str,
    model: str,
    stride: Optional[int],
    aggregation_strategy: str,
    alignment_mode: str,
    spans_key: str,
) -> "_TransformersEntityPipe":
    if hf_pipeline is None:
        raise ImportError(
            "transformers is not installed. Install presidio-analyzer[transformers] "
            "to use TransformersNlpEngine."
        )
    if not model:
        raise ValueError("A Hugging Face token-classification model is required")

    pipeline_kwargs = {
        "task": "token-classification",
        "model": model,
        "aggregation_strategy": aggregation_strategy,
        "device": device_detector.get_device(),
    }
    if stride is not None:
        pipeline_kwargs["stride"] = stride

    pipeline = hf_pipeline(**pipeline_kwargs)
    return _TransformersEntityPipe(
        name=name,
        pipeline=pipeline,
        alignment_mode=alignment_mode,
        spans_key=spans_key,
    )


class _TransformersEntityPipe(Pipe):
    """Add Hugging Face token-classification predictions to a spaCy document."""

    def __init__(
        self,
        name: str,
        pipeline: Any,
        alignment_mode: str,
        spans_key: str,
    ) -> None:
        self.name = name
        self.pipeline = pipeline
        self.alignment_mode = alignment_mode
        self.spans_key = spans_key

    def __call__(self, doc: Doc) -> Doc:
        return self._add_predictions(doc, self.pipeline(doc.text))

    def pipe(
        self, stream: Iterable[Doc], *, batch_size: int = 128
    ) -> Iterator[Doc]:
        for docs in spacy.util.minibatch(stream, size=batch_size):
            docs = list(docs)
            predictions = self.pipeline(
                [doc.text for doc in docs], batch_size=batch_size
            )
            for doc, doc_predictions in zip(docs, predictions, strict=True):
                yield self._add_predictions(doc, doc_predictions)

    def _add_predictions(
        self, doc: Doc, predictions: Iterable[Dict[str, Any]]
    ) -> Doc:
        spans = SpanGroup(doc, name=self.spans_key, attrs={"scores": []})
        previous_end = 0

        for prediction in predictions:
            label = prediction.get("entity_group") or prediction.get("entity")
            start = prediction.get("start")
            end = prediction.get("end")
            if not label or not isinstance(start, int) or not isinstance(end, int):
                logger.warning(
                    "Skipping malformed Transformers prediction: %s", prediction
                )
                continue

            span = doc.char_span(
                start,
                end,
                label=str(label),
                alignment_mode=self.alignment_mode,
            )
            if span is None or span.start_char < previous_end:
                logger.warning(
                    "Skipping unaligned or overlapping Transformers prediction: %s",
                    prediction,
                )
                continue

            spans.append(span)
            spans.attrs["scores"].append(float(prediction.get("score", 0.0)))
            previous_end = span.end_char

        doc.spans[self.spans_key] = spans
        return doc

    def to_bytes(self, **kwargs: Any) -> bytes:
        return b""

    def from_bytes(self, bytes_data: bytes, **kwargs: Any) -> "_TransformersEntityPipe":
        return self

    def to_disk(self, path: Any, **kwargs: Any) -> None:
        return None

    def from_disk(self, path: Any, **kwargs: Any) -> "_TransformersEntityPipe":
        return self


class TransformersNlpEngine(SpacyNlpEngine):
    """

    TransformersNlpEngine is a transformers based NlpEngine.

    It comprises a spacy pipeline used for tokenization,
    lemmatization, pos, and a transformers component for NER.

    Both the underlying spacy pipeline and the transformers engine could be
    configured by the user.
    :param models: A dict holding the model's configuration.
    :example:
    [{"lang_code": "en", "model_name": {
            "spacy": "en_core_web_sm",
            "transformers": "dslim/bert-base-NER"
            }
    }]
    :param ner_model_configuration: Parameters for the NER model.
    See conf/transformers.yaml for an example


    Note that since the spaCy model is not used for NER,
    we recommend using a simple model, such as en_core_web_sm for English.
    For potential Transformers models, see a list of models here:
    https://huggingface.co/models?pipeline_tag=token-classification
    It is further recommended to fine-tune these models
    to the specific scenario in hand.

    """

    engine_name = "transformers"
    is_available = bool(hf_pipeline)

    def __init__(
        self,
        models: Optional[List[Dict]] = None,
        ner_model_configuration: Optional[NerModelConfiguration] = None,
    ):
        if not models:
            models = [
                {
                    "lang_code": "en",
                    "model_name": {
                        "spacy": "en_core_web_sm",
                        "transformers": "obi/deid_roberta_i2b2",
                    },
                }
            ]
        super().__init__(models=models, ner_model_configuration=ner_model_configuration)
        self.entity_key = "bert-base-ner"

    def load(self) -> None:
        """Load the spaCy and transformers models."""

        logger.debug(f"Loading SpaCy and transformers models: {self.models}")

        super()._enable_gpu()

        self.nlp = {}

        for model in self.models:
            self._validate_model_params(model)
            spacy_model = model["model_name"]["spacy"]
            transformers_model = model["model_name"]["transformers"]
            self._download_spacy_model_if_needed(spacy_model)

            nlp = spacy.load(spacy_model, disable=["parser", "ner"])

            pipe_config = {
                "model": transformers_model,
                "stride": self.ner_model_configuration.stride,
                "alignment_mode": self.ner_model_configuration.alignment_mode,
                "aggregation_strategy": self.ner_model_configuration.aggregation_strategy,  # noqa: E501
                "spans_key": self.entity_key,
            }

            nlp.add_pipe(_PIPE_NAME, config=pipe_config)
            self.nlp[model["lang_code"]] = nlp

    @staticmethod
    def _validate_model_params(model: Dict) -> None:
        if "lang_code" not in model:
            raise ValueError("lang_code is missing from model configuration")
        if "model_name" not in model:
            raise ValueError("model_name is missing from model configuration")
        if not isinstance(model["model_name"], dict):
            raise ValueError("model_name must be a dictionary")
        if "spacy" not in model["model_name"]:
            raise ValueError("spacy model name is missing from model configuration")
        if "transformers" not in model["model_name"]:
            raise ValueError(
                "transformers model name is missing from model configuration"
            )

    def _get_entities(self, doc: Doc) -> List[Span]:
        """
        Extract entities out of a spaCy pipeline, depending on the type of pipeline.

        For spacy-huggingface-pipeline, this would be doc.spans[key]
        :param doc: the output spaCy doc.
        :return: List of entities
        """

        return doc.spans[self.entity_key]

    def _get_scores_for_entities(self, doc: Doc) -> List[float]:
        """Extract scores for entities from the doc.

        While spaCy does not provide confidence scores,
        the spacy-huggingface-pipeline flow adds confidence scores
        as SpanGroup attributes.
        :param doc: SpaCy doc
        """

        return [float(score) for score in doc.spans[self.entity_key].attrs["scores"]]
