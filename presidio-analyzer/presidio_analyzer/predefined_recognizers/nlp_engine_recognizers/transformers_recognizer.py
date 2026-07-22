import logging
from typing import Optional

from presidio_analyzer.predefined_recognizers.nlp_engine_recognizers.spacy_recognizer import (  # noqa: E501
    SpacyRecognizer,
)

logger = logging.getLogger("presidio-analyzer")


class TransformersRecognizer(SpacyRecognizer):
    """
    Recognize entities using the spacy-huggingface-pipeline package.

    The recognizer doesn't run transformers models,
    but loads the output from the NlpArtifacts
    See:
     - https://huggingface.co/docs/transformers/main/en/index for transformer models
     - https://huggingface.co/docs/transformers/main_classes/pipelines for the pipeline API
    """  # noqa: E501

    ENTITIES = [
        "PERSON",
        "LOCATION",
        "ORGANIZATION",
        "AGE",
        "ID",
        "EMAIL",
        "DATE_TIME",
        "PHONE_NUMBER",
    ]

    def __init__(self, name: Optional[str] = None, **kwargs):
        self.DEFAULT_EXPLANATION = self.DEFAULT_EXPLANATION.replace(
            "Spacy", "Transformers"
        )
        super().__init__(name=name, **kwargs)
