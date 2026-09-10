"""Medical NER recognizer using HuggingFace pipeline directly."""

from typing import Dict, List, Optional, Union

from presidio_analyzer.chunkers import BaseTextChunker
from presidio_analyzer.predefined_recognizers.ner.huggingface_ner_recognizer import (
    HuggingFaceNerRecognizer,
)

DEFAULT_MEDICAL_ENTITY_MAPPING: Dict[str, str] = {
    "DISEASE_DISORDER": "MEDICAL_DISEASE_DISORDER",
    "MEDICATION": "MEDICAL_MEDICATION",
    "THERAPEUTIC_PROCEDURE": "MEDICAL_THERAPEUTIC_PROCEDURE",
    "CLINICAL_EVENT": "MEDICAL_CLINICAL_EVENT",
    "BIOLOGICAL_ATTRIBUTE": "MEDICAL_BIOLOGICAL_ATTRIBUTE",
    "BIOLOGICAL_STRUCTURE": "MEDICAL_BIOLOGICAL_STRUCTURE",
    "FAMILY_HISTORY": "MEDICAL_FAMILY_HISTORY",
    "HISTORY": "MEDICAL_HISTORY",
}


class MedicalNERRecognizer(HuggingFaceNerRecognizer):
    """Recognize medical/clinical entities using blaze999/Medical-NER.

    Thin subclass of :class:`HuggingFaceNerRecognizer` that sets
    medical-specific defaults. Uses HuggingFace ``transformers.pipeline``
    directly (no spaCy dependency).
    """

    ENTITIES = list(DEFAULT_MEDICAL_ENTITY_MAPPING.values())

    def __init__(
        self,
        model_name: str = "blaze999/Medical-NER",
        label_mapping: Optional[Dict[str, str]] = None,
        supported_entities: Optional[List[str]] = None,
        name: str = "MedicalNERRecognizer",
        supported_language: str = "en",
        aggregation_strategy: str = "simple",
        threshold: float = 0.3,
        device: Optional[Union[str, int]] = None,
        text_chunker: Optional[BaseTextChunker] = None,
    ):
        """Initialize the Medical NER recognizer.

        :param model_name: HuggingFace model name/path.
            Default: ``blaze999/Medical-NER``
        :param label_mapping: Model label -> Presidio entity mapping.
            Default: :data:`DEFAULT_MEDICAL_ENTITY_MAPPING`
        :param supported_entities: Entity types to return (None = all mapped).
        :param name: Recognizer name
        :param supported_language: Language code
        :param aggregation_strategy: Pipeline aggregation strategy
        :param threshold: Minimum confidence score (0.0 - 1.0)
        :param device: Device string/int (None = auto-detect)
        :param text_chunker: Custom text chunker (None = default)
        """
        super().__init__(
            model_name=model_name,
            label_mapping=label_mapping or DEFAULT_MEDICAL_ENTITY_MAPPING,
            supported_entities=supported_entities,
            name=name,
            supported_language=supported_language,
            aggregation_strategy=aggregation_strategy,
            threshold=threshold,
            device=device,
            text_chunker=text_chunker,
        )
