"""Class-local configuration rules independent of registry construction."""

from pydantic import BaseModel, model_validator


def _normalize_legacy_fields(values, legacy_model):
    """Retain old coercions for existing fields without constraining new kwargs."""
    values = dict(values)
    legacy_values = {
        key: value for key, value in values.items() if key in legacy_model.model_fields
    }
    normalized = legacy_model(**legacy_values).model_dump(exclude_unset=True)
    return {**values, **normalized}


class HuggingFaceConfigRules(BaseModel):
    """Preserve legacy HF validation while new constructor fields remain generic."""

    @model_validator(mode="before")
    @classmethod
    def validate_chunker(cls, values):
        """Keep existing scalar coercions and structured chunker validation."""
        from presidio_analyzer.input_validation.yaml_recognizer_models import (
            HuggingFaceRecognizerConfig,
        )

        return _normalize_legacy_fields(values, HuggingFaceRecognizerConfig)


class GLiNERConfigRules(BaseModel):
    """Preserve legacy GLiNER validation without a maintained constructor schema."""

    @model_validator(mode="before")
    @classmethod
    def validate_entity_mapping(cls, values):
        """Keep scalar coercions, chunking and entity-selection rules."""
        from presidio_analyzer.input_validation.yaml_recognizer_models import (
            GLiNERRecognizerConfig,
        )

        return _normalize_legacy_fields(values, GLiNERRecognizerConfig)
