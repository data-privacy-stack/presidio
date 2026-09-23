"""Model-aware configuration identities, checked before recognizer construction."""

import inspect
from typing import Any, Dict, List, Optional, Tuple

from presidio_analyzer._configuration_errors import ConfigValidationError

from .recognizer_configuration import constructor_parameters


def model_identity(recognizer_cls: type, values: Dict[str, Any]) -> Optional[str]:
    """Return an explicit or constructor-default model identifier without loading.

    :param recognizer_cls: Resolved recognizer implementation.
    :param values: Presence-aware recognizer settings.
    :return: String model identifier, or None for non-model configurations.
    """
    parameter = constructor_parameters(recognizer_cls).get("model_name")
    if parameter is None:
        return None
    model = values.get("model_name")
    if model is None and parameter.default is not inspect.Parameter.empty:
        model = parameter.default
    return model if isinstance(model, str) and model else None


def default_recognizer_name(recognizer_cls: type, values: Dict[str, Any]) -> str:
    """Derive a readable instance name only for configurations omitting name.

    :param recognizer_cls: Resolved recognizer implementation.
    :param values: Presence-aware recognizer settings.
    :return: Class name, suffixed with the model identifier when available.
    """
    model = model_identity(recognizer_cls, values)
    return f"{recognizer_cls.__name__}:{model}" if model else recognizer_cls.__name__


def validate_registry_identities(
    entries: List[Tuple[Dict[str, Any], bool]], supported_languages: List[str]
) -> None:
    """Reject ambiguous active identities across expanded, supported languages.

    :param entries: Validated entries paired with whether name was explicit.
    :param supported_languages: Registry language filter.
    :raises ValueError: Names collide or repeated models have implicit names.
    """
    from presidio_analyzer.recognizer_registry.recognizers_loader_utils import (
        PredefinedRecognizerNotFoundError,
        RecognizerListLoader,
    )

    names = {}
    models = {}
    for index, (entry, explicit_name) in enumerate(entries):
        if not entry.get("enabled", True):
            continue
        recognizer_cls = None
        model = None
        if entry.get("type", "predefined") == "predefined":
            try:
                recognizer_cls = RecognizerListLoader.get_existing_recognizer_cls(
                    entry.get("class_name") or entry["name"]
                )
            except PredefinedRecognizerNotFoundError as exc:
                raise ConfigValidationError(
                    f"Predefined recognizer {entry['name']!r} at entry {index} "
                    "not found; "
                    "use a registered class name.",
                    code="unknown_class",
                    path=(index,),
                    safe_message=(
                        "Unknown recognizer class; use a registered class name. "
                        f"Suggestions: {list(exc.suggestions)}."
                    ),
                ) from exc
            model = model_identity(recognizer_cls, entry)
        for language_conf in RecognizerListLoader._get_recognizer_languages(
            entry, supported_languages
        ):
            language = language_conf["supported_language"]
            if language not in supported_languages:
                continue
            name_key = (entry["name"], language)
            if name_key in names:
                if names[name_key] == index:
                    raise ConfigValidationError(
                        f"Duplicate recognizer language {language} at entry {index}; "
                        "remove repeated language codes from the entry or registry.",
                        code="duplicate_identity",
                        path=(index,),
                    )
                raise ConfigValidationError(
                    f"Duplicate recognizer name {entry['name']!r} for language "
                    f"{language} at entries "
                    f"{names[name_key]} and {index}; choose distinct names.",
                    code="duplicate_identity",
                    path=(index,),
                    safe_message=(
                        f"Duplicate recognizer identity at entries {names[name_key]} "
                        f"and {index}; choose distinct names for each language."
                    ),
                )
            names[name_key] = index
            if model is not None:
                model_key = (recognizer_cls, model, language)
                previous = models.get(model_key)
                if previous is not None and not (previous[1] and explicit_name):
                    raise ConfigValidationError(
                        f"Repeated model for {recognizer_cls.__name__} at entries "
                        f"{previous[0]} and {index} for "
                        f"language {language} requires explicit unique names on "
                        "every instance.",
                        code="repeated_model",
                        path=(index,),
                        safe_message=(
                            "Repeated models require explicit unique names on every "
                            f"instance (entries {previous[0]} and {index})."
                        ),
                    )
                models[model_key] = (index, explicit_name)
