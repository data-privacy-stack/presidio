"""Shared validation for recognizers' explicit library-option blocks."""

import inspect
import logging
import warnings
from typing import Any, Dict, Mapping, Optional

logger = logging.getLogger("presidio-analyzer")


def validate_model_options(
    recognizer_cls: type,
    blocks: Mapping[str, Optional[Dict[str, Any]]],
    legacy_kwargs: Optional[Mapping[str, Any]] = None,
) -> None:
    """Reject ambiguous or malformed blocks before loading a model.

    :param recognizer_cls: Recognizer declaring the named constructor options.
    :param blocks: Named model or prediction option dictionaries.
    :param legacy_kwargs: Deprecated flat model options, if supported.
    :raises ValueError: A block is malformed or repeats an authoritative setting.
    """
    # An ancestor can bind options even when a subclass does not forward **kwargs.
    named = set()
    for base in recognizer_cls.__mro__:
        initializer = base.__dict__.get("__init__")
        if initializer is not None:
            named.update(
                parameter.name
                for parameter in inspect.signature(initializer).parameters.values()
                if parameter.name != "self"
                and parameter.kind
                not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            )
    reserved = getattr(recognizer_cls, "_MODEL_OPTION_RESERVED_KEYS", {})
    for block, options in blocks.items():
        if options is None:
            continue
        if not isinstance(options, dict):
            raise ValueError(f"{block} must be a dictionary")
        if any(not isinstance(key, str) for key in options):
            raise ValueError(f"{block} keys must be strings")
        overlap = set(options) & (named | set(reserved.get(block, ())))
        if overlap:
            raise ValueError(
                f"{recognizer_cls.__name__}.{block} repeats named or reserved "
                f"arguments: {sorted(overlap)}. Configure named settings at the "
                "recognizer level; invocation arguments cannot be overridden."
            )
    duplicate = set(legacy_kwargs or {}) & set(blocks.get("model_kwargs") or {})
    if duplicate:
        raise ValueError(
            f"Options appear both at the top level and in model_kwargs: "
            f"{sorted(duplicate)}. Keep each option in model_kwargs only."
        )
    legacy_overlap = set(legacy_kwargs or {}) & set(reserved.get("model_kwargs", ()))
    if legacy_overlap:
        raise ValueError(
            f"{recognizer_cls.__name__} received reserved flat model options: "
            f"{sorted(legacy_overlap)}. Use the corresponding named recognizer setting."
        )


def warn_legacy_options(
    recognizer_name: str, kwargs: Mapping[str, Any], destination: Optional[str]
) -> None:
    """Warn about deprecated flat options without logging their values.

    :param recognizer_name: Recognizer implementation name.
    :param kwargs: Deprecated flat options.
    :param destination: Replacement block, or None for ignored options.
    """
    if not kwargs:
        return
    action = (
        f"Move them into {destination}."
        if destination
        else "These unsupported options are ignored; use the documented configuration."
    )
    message = (
        f"{recognizer_name} received deprecated flat options {sorted(kwargs)}. "
        f"{action} They will be rejected in the next major release."
    )
    warnings.warn(message, DeprecationWarning, stacklevel=3)
    logger.warning(message)
