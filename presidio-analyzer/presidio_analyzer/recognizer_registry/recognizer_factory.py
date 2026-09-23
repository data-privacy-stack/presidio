"""Presence-aware configuration normalization and shared recognizer construction."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Type

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer
from presidio_analyzer._configuration_errors import ConfigValidationError
from presidio_analyzer.input_validation.recognizer_configuration import (
    constructor_parameters,
    required_constructor_parameters,
)
from presidio_analyzer.score_thresholds import normalize_score_thresholds

logger = logging.getLogger("presidio-analyzer")


@dataclass(frozen=True)
class RecognizerSpec:
    """Validated construction settings for one recognizer and language.

    :param recognizer_cls: Resolved implementation.
    :param name: Configured instance identity.
    :param supported_language: Expanded instance language.
    :param constructor_kwargs: Only present, accepted constructor settings.
    :param attributes: Present registry overrides applied after construction.
    """

    recognizer_cls: Type[EntityRecognizer]
    name: str
    supported_language: str
    constructor_kwargs: Dict[str, Any]
    attributes: Dict[str, Any]


class RecognizerFactory:
    """Normalize and build registry entries identically for every public loader."""

    @staticmethod
    def prepare_kwargs(
        values: Dict[str, Any], recognizer_cls: Type[EntityRecognizer]
    ) -> Dict[str, Any]:
        """Reconcile registry entities and context with the reachable constructor.

        :param values: Settings for a single expanded language.
        :param recognizer_cls: Recognizer implementation.
        :return: Constructor kwargs, without ignored registry metadata.
        """
        kwargs = {key: value for key, value in values.items() if value is not None}
        reachable = constructor_parameters(recognizer_cls)
        singular = "supported_entity" in reachable
        plural = "supported_entities" in reachable
        if singular and not plural and "supported_entities" in kwargs:
            entities = kwargs.pop("supported_entities")
            if entities:
                kwargs.setdefault("supported_entity", entities[0])
        elif plural and not singular and "supported_entity" in kwargs:
            kwargs.setdefault("supported_entities", [kwargs.pop("supported_entity")])
        elif not singular and not plural:
            unused = [
                key
                for key in ("supported_entity", "supported_entities")
                if key in kwargs
            ]
            if unused:
                logger.warning(
                    "%s does not apply 'supported_entity' or 'supported_entities'; "
                    "ignoring %s because it defines entities in its own configuration.",
                    recognizer_cls.__name__,
                    " and ".join(unused),
                )
                for key in unused:
                    kwargs.pop(key)

        if "context" in kwargs and "context" not in reachable:
            context = kwargs.pop("context")
            if context:
                logger.warning(
                    "%s does not accept 'context'; ignoring the context words "
                    "configured for it. Multi-entity recognizers may not support "
                    "context scoring.",
                    recognizer_cls.__name__,
                )
        for key in ("name", "supported_language"):
            if key not in reachable:
                kwargs.pop(key, None)
        return kwargs

    @staticmethod
    def create_specs(configuration: Dict[str, Any]) -> List[RecognizerSpec]:
        """Validate and normalize a registry without constructing any recognizer.

        :param configuration: Registry mapping, without implicit shipped entries.
        :return: One presence-aware spec per active, supported language.
        :raises ValueError: The registry configuration is invalid.
        """
        from presidio_analyzer.input_validation import ConfigurationValidator

        from .recognizers_loader_utils import RecognizerListLoader

        config = ConfigurationValidator.validate_recognizer_registry_configuration(
            configuration
        )
        languages = config["supported_languages"]
        if languages is None:
            languages = ["en"]
        specs = []
        entries = list(
            enumerate(
                {"name": entry, "type": "predefined"}
                if isinstance(entry, str)
                else entry
                for entry in config["recognizers"]
            )
        )
        # Keep the historical predefined-before-custom registry ordering.
        entries.sort(key=lambda item: item[1]["type"] == "custom")
        for entry_index, entry in entries:
            if not entry.get("enabled", True):
                continue
            custom = entry["type"] == "custom"
            recognizer_cls = (
                PatternRecognizer
                if custom
                else RecognizerListLoader.get_existing_recognizer_cls(
                    RecognizerListLoader.get_recognizer_name(entry)
                )
            )
            if not custom:
                RecognizerListLoader._validate_yaml_country_code(
                    entry, recognizer_cls, recognizer_cls.__name__
                )
            for language_config in RecognizerListLoader._get_recognizer_languages(
                entry, languages
            ):
                language = language_config["supported_language"]
                if language not in languages:
                    logger.warning(
                        "%s not added: language %s is not supported by registry.",
                        recognizer_cls.__name__,
                        language,
                    )
                    continue
                values = {
                    key: value
                    for key, value in entry.items()
                    if key
                    not in {
                        "type",
                        "enabled",
                        "class_name",
                        "supported_languages",
                        "score_thresholds",
                    }
                    and (key != "country_code" or custom)
                }
                values.update(language_config)
                kwargs = RecognizerFactory.prepare_kwargs(values, recognizer_cls)
                patterns = (
                    kwargs.get("patterns", [])
                    if issubclass(recognizer_cls, PatternRecognizer)
                    else []
                )
                for index, pattern in enumerate(patterns):
                    try:
                        Pattern.from_dict(pattern)
                    except ValueError as exc:
                        position = getattr(exc.__context__, "pos", None)
                        location = (
                            f" at position {position}" if position is not None else ""
                        )
                        raise ConfigValidationError(
                            f"{recognizer_cls.__name__}: invalid patterns[{index}] "
                            f"regex syntax{location}; correct the pattern definition.",
                            code="pattern_regex",
                            path=(
                                "recognizers",
                                entry_index,
                                "patterns",
                                index,
                                "regex",
                            ),
                        ) from None
                missing = [
                    key
                    for key in sorted(required_constructor_parameters(recognizer_cls))
                    if key not in kwargs
                ]
                if missing:
                    raise ConfigValidationError(
                        f"{recognizer_cls.__name__} requires constructor settings "
                        f"after language/entity normalization: {missing}",
                        code="missing_setting",
                        path=("recognizers", entry_index, missing[0]),
                    )
                attributes = {
                    key: values[key]
                    for key in ("name", "supported_language")
                    if key not in kwargs
                }
                if issubclass(recognizer_cls, PatternRecognizer):
                    if (
                        "global_regex_flags" not in kwargs
                        and config["global_regex_flags"] is not None
                    ):
                        attributes["global_regex_flags"] = config["global_regex_flags"]
                    elif config["global_regex_flags"] is None:
                        logger.debug(
                            "global_regex_flags is None; preserving recognizer defaults"
                        )
                if "score_thresholds" in entry:
                    attributes["score_thresholds"] = normalize_score_thresholds(
                        entry["score_thresholds"]
                    )
                specs.append(
                    RecognizerSpec(
                        recognizer_cls, entry["name"], language, kwargs, attributes
                    )
                )
        return specs

    @staticmethod
    def build(spec: RecognizerSpec) -> EntityRecognizer:
        """Construct one validated spec and apply only present registry overrides.

        :param spec: Normalized construction settings.
        :return: Constructed recognizer.
        """
        kwargs = dict(spec.constructor_kwargs)
        if (
            "patterns" in kwargs
            and issubclass(spec.recognizer_cls, PatternRecognizer)
            and spec.recognizer_cls is not PatternRecognizer
        ):
            kwargs["patterns"] = [Pattern.from_dict(p) for p in kwargs["patterns"]]
        if isinstance(kwargs.get("text_chunker"), dict):
            from presidio_analyzer.chunkers import TextChunkerProvider

            kwargs["text_chunker"] = TextChunkerProvider(
                {
                    key: value
                    for key, value in kwargs["text_chunker"].items()
                    if value is not None
                }
            ).create_chunker()
        recognizer = (
            PatternRecognizer.from_dict(kwargs)
            if spec.recognizer_cls is PatternRecognizer
            else spec.recognizer_cls(**kwargs)
        )
        for key, value in spec.attributes.items():
            setattr(recognizer, key, value)
        return recognizer

    @staticmethod
    def build_all(
        specs: Iterable[RecognizerSpec],
        existing: Iterable[EntityRecognizer] = (),
    ) -> List[EntityRecognizer]:
        """Check identities before building or adding any configured recognizer.

        :param specs: Normalized settings to build.
        :param existing: Already registered recognizers for duplicate checks.
        :return: Constructed recognizers, without mutating an existing registry.
        :raises ValueError: A name/language identity already exists.
        """
        specs = list(specs)
        identities = {(r.name, r.supported_language) for r in existing}
        for spec in specs:
            identity = (spec.name, spec.supported_language)
            if identity in identities:
                raise ValueError(
                    f"Duplicate recognizer name {spec.name!r} for language "
                    f"{spec.supported_language}; choose a distinct name."
                )
            identities.add(identity)
        return [RecognizerFactory.build(spec) for spec in specs]
