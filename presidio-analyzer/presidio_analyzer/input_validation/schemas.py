from pathlib import Path
from typing import Any, Dict, List, Union

from pydantic import ValidationError

from . import validate_language_codes
from .yaml_recognizer_models import RecognizerRegistryConfig


class ConfigurationValidator:
    """Class for validating configurations using Pydantic-enabled classes."""

    @staticmethod
    def validate_language_codes(languages: List[str]) -> List[str]:
        """Validate language codes format.

        :param languages: List of languages to validate.
        """
        validate_language_codes(languages)
        return languages

    @staticmethod
    def validate_file_path(file_path: Union[str, Path]) -> Path:
        """Validate file path exists and is readable.

        :param file_path: Path to validate.
        """
        path = Path(file_path)
        if not path.exists():
            raise ValueError(f"Configuration file does not exist: {path}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {path}")
        return path

    @staticmethod
    def validate_score_threshold(threshold: float) -> float:
        """Validate score threshold is within valid range.

        :param threshold: score threshold to validate.
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(
                f"Score threshold must be between 0.0 and 1.0, got: {threshold}"
            )
        return threshold

    @staticmethod
    def validate_recognizer_score_thresholds(
        thresholds: Dict[str, Any],
    ) -> Dict[str, Dict[str, float]]:
        """Validate recognizer-specific score thresholds."""
        if not isinstance(thresholds, dict):
            raise ValueError("recognizer_score_thresholds must be a dictionary")

        validated_thresholds: Dict[str, Dict[str, float]] = {}
        for recognizer_name, recognizer_thresholds in thresholds.items():
            if (
                not isinstance(recognizer_name, str)
                or recognizer_name.strip() != recognizer_name
                or not recognizer_name
            ):
                raise ValueError(
                    "recognizer_score_thresholds keys must be non-empty strings"
                )

            if isinstance(recognizer_thresholds, (int, float)) and not isinstance(
                recognizer_thresholds, bool
            ):
                validated_thresholds[recognizer_name] = {
                    "default": ConfigurationValidator.validate_score_threshold(
                        recognizer_thresholds
                    )
                }
                continue

            if not isinstance(recognizer_thresholds, dict):
                raise ValueError(
                    f"Thresholds for recognizer '{recognizer_name}' "
                    f"must be a dictionary"
                )

            validated_recognizer_thresholds: Dict[str, float] = {}
            for threshold_name, threshold_value in recognizer_thresholds.items():
                if (
                    not isinstance(threshold_name, str)
                    or threshold_name.strip() != threshold_name
                    or not threshold_name
                ):
                    raise ValueError(
                        "recognizer_score_thresholds nested keys must be "
                        "non-empty strings"
                    )

                validated_recognizer_thresholds[threshold_name] = (
                    ConfigurationValidator.validate_score_threshold(threshold_value)
                )

            validated_thresholds[recognizer_name] = validated_recognizer_thresholds

        return validated_thresholds

    @staticmethod
    def validate_nlp_configuration(config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate NLP configuration structure.

        :param config: NLP Configuration to validate.
        """
        if not isinstance(config, dict):
            raise ValueError("NLP configuration must be a dictionary")

        required_fields = ["nlp_engine_name", "models"]
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            raise ValueError(
                f"NLP configuration missing required fields: {missing_fields}"
            )

        # Validate models structure
        if not isinstance(config["models"], list) or not config["models"]:
            raise ValueError("Models must be a non-empty list")

        for model in config["models"]:
            if not isinstance(model, dict):
                raise ValueError("Each model must be a dictionary")
            if "lang_code" not in model or "model_name" not in model:
                raise ValueError("Each model must have 'lang_code' and 'model_name'")

        return config

    @staticmethod
    def validate_recognizer_registry_configuration(
        config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate recognizer registry configuration using Pydantic models."""
        try:
            # Use Pydantic model for validation
            validated_config = RecognizerRegistryConfig(**config)
            return ConfigurationValidator._dump_recognizer_registry_configuration(
                validated_config
            )
        except ValidationError as e:
            raise ValueError("Invalid recognizer registry configuration") from e

    @staticmethod
    def _dump_recognizer_registry_configuration(
        validated_config: RecognizerRegistryConfig,
    ) -> Dict[str, Any]:
        """Dump registry config while preserving recognizer-specific dump rules."""
        dumped_config = validated_config.model_dump(
            exclude_unset=False, exclude={"recognizers"}
        )
        dumped_config["recognizers"] = [
            recognizer
            if isinstance(recognizer, str)
            else recognizer.model_dump()
            for recognizer in validated_config.recognizers
        ]
        return dumped_config

    @staticmethod
    def validate_analyzer_configuration(config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate analyzer engine configuration."""
        if not isinstance(config, dict):
            raise ValueError("Analyzer configuration must be a dictionary")

        # Define valid top-level keys for analyzer configuration
        valid_keys = {
            "supported_languages",
            "default_score_threshold",
            "recognizer_score_thresholds",
            "nlp_configuration",
            "recognizer_registry",
        }

        # Check for unknown keys
        unknown_keys = set(config.keys()) - valid_keys
        if unknown_keys:
            raise ValueError(
                f"Unknown configuration key(s) in "
                f"analyzer configuration: {sorted(unknown_keys)}. "
                f"Valid keys are: {sorted(valid_keys)}"
            )

        # Validate supported languages if present
        if "supported_languages" in config:
            validate_language_codes(config["supported_languages"])

        # Validate score threshold if present
        if "default_score_threshold" in config:
            ConfigurationValidator.validate_score_threshold(
                config["default_score_threshold"]
            )

        if "recognizer_score_thresholds" in config:
            config["recognizer_score_thresholds"] = (
                ConfigurationValidator.validate_recognizer_score_thresholds(
                config["recognizer_score_thresholds"]
            )
            )

        # Validate nested configurations
        if "nlp_configuration" in config:
            ConfigurationValidator.validate_nlp_configuration(
                config["nlp_configuration"]
            )

        if "recognizer_registry" in config:
            ConfigurationValidator.validate_recognizer_registry_configuration(
                config["recognizer_registry"]
            )

        return config
