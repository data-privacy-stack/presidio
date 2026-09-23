"""Standalone, model-free registry validation with value-safe diagnostics."""

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import ValidationError

from presidio_analyzer._configuration_errors import ConfigPath, ConfigValidationError

_SAFE_MESSAGES = {
    "missing": "Field is required.",
    "string_type": "Value must be a string.",
    "int_type": "Value must be an integer.",
    "int_parsing": "Value must be a valid integer.",
    "float_type": "Value must be a number.",
    "float_parsing": "Value must be a valid number.",
    "bool_type": "Value must be a boolean.",
    "bool_parsing": "Value must be a valid boolean.",
    "list_type": "Value must be a list.",
    "dict_type": "Value must be a mapping.",
    "extra_forbidden": "Unknown configuration key; remove it or check its spelling.",
    "literal_error": "Use one of the values allowed by the schema.",
    "greater_than_equal": "Value is below the minimum allowed by the schema.",
    "less_than_equal": "Value exceeds the maximum allowed by the schema.",
    "value_error": "Invalid configuration settings; check language, entity, context "
    "and constructor options for this entry.",
}


@dataclass(frozen=True)
class ConfigError:
    """One configuration diagnostic, excluding input values and exception objects.

    :param path: Field path, with zero-based recognizer/pattern indices.
    :param code: Stable diagnostic category.
    :param message: Actionable text safe to display without raw configuration values.
    """

    path: ConfigPath
    code: str
    message: str


def _input_path(path: ConfigPath, configuration: Dict[str, Any]) -> ConfigPath:
    """Remove Pydantic union labels while keeping actual input keys."""
    current: Any = configuration
    result = []
    for part in path:
        if isinstance(current, dict) and part in current:
            result.append(part)
            current = current[part]
        elif isinstance(current, list) and isinstance(part, int):
            result.append(part)
            current = current[part] if 0 <= part < len(current) else None
        elif isinstance(part, str) and ("[" in part or part == "str"):
            continue
        else:
            result.append(part)
            current = None
    return tuple(result)


def _diagnostics(exc: ValueError, configuration: Dict[str, Any]) -> List[ConfigError]:
    if isinstance(exc, ConfigValidationError):
        return [ConfigError(exc.path, exc.code, exc.safe_message)]
    validation = exc if isinstance(exc, ValidationError) else exc.__cause__
    if not isinstance(validation, ValidationError):
        return [
            ConfigError(
                (),
                "value_error",
                "Invalid registry settings; check required constructor options "
                "and the configured language/entity combinations.",
            )
        ]
    errors = []
    for error in validation.errors(include_input=False, include_url=False):
        path = _input_path(tuple(error["loc"]), configuration)
        cause = error.get("ctx", {}).get("error")
        if isinstance(cause, ConfigValidationError):
            errors.append(
                ConfigError(path + cause.path, cause.code, cause.safe_message)
            )
        else:
            code = error["type"] if error["type"] in _SAFE_MESSAGES else "value_error"
            errors.append(ConfigError(path, code, _SAFE_MESSAGES[code]))
    return errors


def _check(configuration: Dict[str, Any]) -> List[ConfigError]:
    from presidio_analyzer.recognizer_registry import RecognizerFactory

    try:
        RecognizerFactory.create_specs(configuration)
    except ValueError as exc:
        return _diagnostics(exc, configuration)
    return []


def validate_registry_config(
    path_or_dict: Union[str, Path, Dict[str, Any]],
    *,
    strict: Optional[bool] = None,
) -> List[ConfigError]:
    """Validate registry configuration without loading models or using defaults.

    Valid configurations return an empty list. Compatibility warnings remain
    warnings unless strict mode is requested. Arbitrary custom-validator exception
    text is not exposed because it may contain configuration secrets.

    :param path_or_dict: YAML file path or complete registry mapping.
    :param strict: Optional override of the configuration's unknown-key policy.
    :return: Structured errors, including independent invalid recognizer entries.
    """
    if isinstance(path_or_dict, (str, Path)):
        try:
            with open(path_or_dict, encoding="utf-8") as stream:
                configuration = yaml.safe_load(stream)
        except OSError:
            return [
                ConfigError(
                    (),
                    "file_read",
                    "Cannot read configuration; check path and file permissions.",
                )
            ]
        except (yaml.YAMLError, UnicodeError) as exc:
            mark = getattr(exc, "problem_mark", None)
            position = (
                f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
            )
            return [
                ConfigError(
                    (), "yaml_syntax", f"Invalid YAML syntax or encoding{position}."
                )
            ]
    else:
        configuration = path_or_dict
    if not isinstance(configuration, dict):
        return [
            ConfigError((), "mapping_type", "Registry configuration must be a mapping.")
        ]
    if any(not isinstance(key, str) for key in configuration):
        return [ConfigError((), "mapping_keys", "Registry keys must be strings.")]
    configuration = dict(configuration)
    if strict is not None:
        configuration["strict"] = strict
    complete_errors = _check(configuration)
    if not complete_errors:
        return []
    entries = configuration.get("recognizers")
    if not isinstance(entries, list) or not entries:
        return complete_errors

    errors = []
    valid_entries = []
    valid_indices = []
    for index, entry in enumerate(entries):
        entry_errors = _check({**configuration, "recognizers": [entry]})
        if not entry_errors:
            valid_entries.append(entry)
            valid_indices.append(index)
        for error in entry_errors:
            if error.path and error.path[0] == "recognizers":
                suffix = error.path[1:]
                if suffix and isinstance(suffix[0], int):
                    suffix = suffix[1:]
                error = replace(error, path=("recognizers", index) + suffix)
            elif not error.path or error.path[0] not in configuration:
                error = replace(error, path=("recognizers", index) + error.path)
            errors.append(error)
    if len(valid_entries) > 1:
        for error in _check({**configuration, "recognizers": valid_entries}):
            if (
                len(error.path) > 1
                and error.path[0] == "recognizers"
                and isinstance(error.path[1], int)
            ):
                error = replace(
                    error,
                    path=("recognizers", valid_indices[error.path[1]]) + error.path[2:],
                )
            errors.append(error)
    result = list(dict.fromkeys(errors or complete_errors))
    return sorted(
        result, key=lambda error: bool(error.path and error.path[0] == "recognizers")
    )
