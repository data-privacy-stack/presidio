"""Configuration validation module for Presidio."""

from .language_validation import validate_language_codes
from .recognizer_configuration import derive_config_model
from .registry_validation import ConfigError, validate_registry_config
from .schema_export import export_registry_schema, render_recognizer_config_reference
from .schemas import ConfigurationValidator
from .yaml_recognizer_models import (
    BaseRecognizerConfig,
    CustomRecognizerConfig,
    GLiNERRecognizerConfig,
    HuggingFaceRecognizerConfig,
    LanguageContextConfig,
    PredefinedRecognizerConfig,
    RecognizerRegistryConfig,
)

__all__ = [
    "validate_language_codes",
    "ConfigurationValidator",
    "derive_config_model",
    "ConfigError",
    "validate_registry_config",
    "export_registry_schema",
    "render_recognizer_config_reference",
    "BaseRecognizerConfig",
    "CustomRecognizerConfig",
    "GLiNERRecognizerConfig",
    "HuggingFaceRecognizerConfig",
    "LanguageContextConfig",
    "PredefinedRecognizerConfig",
    "RecognizerRegistryConfig",
]
