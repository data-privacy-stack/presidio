"""Constructor-derived recognizer schemas and unknown-key policy."""

import inspect
import logging
import warnings
from difflib import get_close_matches
from functools import lru_cache
from typing import Any, Dict, Type

from pydantic import BaseModel, ConfigDict, create_model

from presidio_analyzer._model_options import validate_model_options, warn_legacy_options

logger = logging.getLogger("presidio-analyzer")


def constructor_parameters(recognizer_cls: type) -> Dict[str, inspect.Parameter]:
    """Return keyword parameters reachable through forwarding constructors.

    :param recognizer_cls: Recognizer implementation to inspect.
    :return: Most-specific parameter declarations along its forwarding MRO.
    """
    parameters = {}
    for base in recognizer_cls.__mro__:
        initializer = base.__dict__.get("__init__")
        if initializer is None:
            continue
        signature = inspect.signature(initializer)
        for parameter in signature.parameters.values():
            if parameter.name != "self" and parameter.kind in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            ):
                parameters.setdefault(parameter.name, parameter)
        if base.__dict__.get("CONFIG_LEGACY_KWARGS") or not any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in signature.parameters.values()
        ):
            break
    return parameters


def derive_config_model(recognizer_cls: type, custom: bool = False) -> Type[BaseModel]:
    """Derive a presence-aware YAML schema without constructing a recognizer.

    :param recognizer_cls: Recognizer implementation.
    :param custom: Use the custom-pattern registry contract.
    :return: Cached Pydantic model with Any-typed new constructor fields.
    """
    return _derive_config_model(recognizer_cls, custom)


def required_constructor_parameters(recognizer_cls: type) -> set:
    """Return required keywords on the invoked constructor, not its parents.

    A forwarding subclass may bind required parent arguments in its own body.

    :param recognizer_cls: Recognizer implementation to inspect.
    :return: Required keyword names visible to the caller.
    """
    return {
        name
        for name, parameter in inspect.signature(
            recognizer_cls.__init__
        ).parameters.items()
        if name != "self"
        and parameter.default is inspect.Parameter.empty
        and parameter.kind
        in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    }


@lru_cache(maxsize=None)
def _derive_config_model(recognizer_cls: type, custom: bool) -> Type[BaseModel]:
    from .yaml_recognizer_models import (
        CustomRecognizerConfig,
        PredefinedRecognizerConfig,
    )

    base = CustomRecognizerConfig if custom else PredefinedRecognizerConfig
    rules = getattr(recognizer_cls, "CONFIG_MODEL", None)
    if rules is not None and (
        not isinstance(rules, type) or not issubclass(rules, BaseModel)
    ):
        raise ValueError(
            f"{recognizer_cls.__name__}.CONFIG_MODEL must be a Pydantic model class"
        )
    bases = (base, rules) if rules else (base,)
    existing = set(base.model_fields) | (set(rules.model_fields) if rules else set())
    fields = {
        name: (Any, None)
        for name in constructor_parameters(recognizer_cls)
        if name not in existing
    }
    return create_model(
        f"{recognizer_cls.__name__}RegistryConfig",
        __base__=bases,
        __config__=ConfigDict(extra="forbid", arbitrary_types_allowed=True),
        **fields,
    )


def parse_recognizer_config(
    recognizer_cls: type, values: Dict[str, Any], strict: bool, custom: bool = False
) -> BaseModel:
    """Validate an entry and report unsupported keys before model loading.

    :param recognizer_cls: Resolved recognizer implementation.
    :param values: Registry entry, including normalized type.
    :param strict: Reject unknown keys rather than warn.
    :param custom: Use custom-pattern validation rules.
    :return: Validated model preserving explicit field presence.
    :raises ValueError: Configuration keys or option blocks are invalid.
    """
    model = derive_config_model(recognizer_cls, custom)
    values = dict(values)
    if not custom and "name" not in values:
        from .recognizer_identity import default_recognizer_name

        values["name"] = default_recognizer_name(recognizer_cls, values)
    accepted = set(model.model_fields)
    unknown = set(values) - accepted
    legacy = getattr(recognizer_cls, "CONFIG_LEGACY_KWARGS", None)
    if unknown:
        message = (
            f"{recognizer_cls.__name__} does not accept {sorted(unknown)}. "
            f"Accepted keys: {sorted(accepted)}."
        )
        suggestions = {
            key: get_close_matches(key, sorted(accepted), n=1)
            for key in sorted(unknown)
        }
        suggestions = {key: match[0] for key, match in suggestions.items() if match}
        if suggestions:
            message += f" Did you mean: {suggestions}?"
        if strict:
            raise ValueError(message)
        extras = {key: values.pop(key) for key in unknown}
        if legacy == "model_kwargs":
            validate_model_options(
                recognizer_cls,
                {
                    "model_kwargs": values.get("model_kwargs"),
                    "predict_kwargs": values.get("predict_kwargs"),
                },
                legacy_kwargs=extras,
            )
            warn_legacy_options(recognizer_cls.__name__, extras, "model_kwargs")
            values["model_kwargs"] = {**extras, **(values.get("model_kwargs") or {})}
        else:
            warnings.warn(message, DeprecationWarning, stacklevel=3)
            logger.warning(message)

    blocks = {
        name: values.get(name)
        for name in ("model_kwargs", "predict_kwargs", "tokenizer_kwargs")
        if name in accepted
    }
    if blocks:
        validate_model_options(recognizer_cls, blocks)
    if values.get("enabled", True):
        missing = [
            name
            for name in sorted(required_constructor_parameters(recognizer_cls))
            if name not in values
            and name
            not in ("supported_entity", "supported_entities", "supported_language")
        ]
        if missing:
            raise ValueError(
                f"{recognizer_cls.__name__} requires constructor settings: {missing}"
            )
    return model(**values)
