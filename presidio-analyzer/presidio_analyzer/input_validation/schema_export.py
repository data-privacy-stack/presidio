"""JSON Schema and accepted-key documentation from runtime-derived models."""

import re
from typing import Any, Dict, Iterable, List, Optional, Type

from pydantic.json_schema import models_json_schema

from presidio_analyzer import EntityRecognizer, PatternRecognizer

from .recognizer_configuration import (
    constructor_parameters,
    derive_config_model,
    required_constructor_parameters,
)
from .yaml_recognizer_models import BaseRecognizerConfig, RecognizerRegistryConfig


def _classes(
    additional: Optional[Iterable[Type[EntityRecognizer]]] = None,
) -> List[Type[EntityRecognizer]]:
    from presidio_analyzer import predefined_recognizers

    exported = [
        getattr(predefined_recognizers, name) for name in predefined_recognizers.__all__
    ]
    classes = [
        cls
        for cls in exported
        if isinstance(cls, type) and issubclass(cls, EntityRecognizer)
    ]
    classes.extend([PatternRecognizer, *(additional or ())])
    if any(
        not isinstance(cls, type) or not issubclass(cls, EntityRecognizer)
        for cls in classes
    ):
        raise ValueError("Schema exports require EntityRecognizer classes")
    by_name = {}
    for cls in classes:
        if cls.__name__ in by_name and by_name[cls.__name__] is not cls:
            raise ValueError("Schema export classes must have unique class names")
        by_name[cls.__name__] = cls
    return [by_name[name] for name in sorted(by_name)]


def _pattern_schema() -> Dict[str, Any]:
    return {
        "anyOf": [
            {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "regex": {"type": "string"},
                        "score": {"type": "number", "minimum": 0, "maximum": 1},
                    },
                    "required": ["name", "regex", "score"],
                    "additionalProperties": False,
                },
            },
            {"type": "null"},
        ]
    }


def export_registry_schema(
    recognizer_classes: Optional[Iterable[Type[EntityRecognizer]]] = None,
    *,
    strict: bool = False,
) -> Dict[str, Any]:
    """Export a Draft 2020-12 schema without loading models or tokenizers.

    The schema covers bundled public recognizers and optional additional classes.
    Semantic checks, coercions and cross-field class validators remain authoritative
    in ``validate_registry_config``.

    :param recognizer_classes: Additional application-specific recognizer classes.
    :param strict: Reject unknown entry keys even when the registry omits strict.
    :return: JSON-serializable registry schema with shared definitions.
    """
    classes = _classes(recognizer_classes)
    models = [derive_config_model(cls) for cls in classes]
    custom_model = derive_config_model(PatternRecognizer, custom=True)
    references, definitions = models_json_schema(
        [(model, "validation") for model in [*models, custom_model]]
    )
    entry_refs = []
    for cls, model in [*zip(classes, models), (PatternRecognizer, custom_model)]:
        reference = references[(model, "validation")]
        entry_refs.append(reference)
        entry = definitions["$defs"][reference["$ref"].split("/")[-1]]
        entry.pop("additionalProperties", None)
        properties = entry["properties"]
        for field in constructor_parameters(cls):
            if field in properties:
                properties[field].pop("default", None)
        for block in ("model_kwargs", "predict_kwargs", "tokenizer_kwargs"):
            if block in properties:
                properties[block] = {"type": ["object", "null"]}
        if issubclass(cls, PatternRecognizer) and "patterns" in properties:
            properties["patterns"] = _pattern_schema()
        entry["required"] = []
        if model is custom_model:
            properties["type"] = {"enum": ["custom", None]}
            entry["allOf"] = [
                {
                    "anyOf": [
                        {"required": ["supported_entity"]},
                        {"required": ["supported_entities"]},
                    ]
                },
                {
                    "anyOf": [
                        {
                            "required": [key],
                            "properties": {key: {"type": "array", "minItems": 1}},
                        }
                        for key in ("patterns", "deny_list")
                    ]
                },
            ]
        else:
            properties["type"] = {"enum": ["predefined", None]}
            entry["allOf"] = [
                {
                    "anyOf": [
                        {
                            "required": ["class_name"],
                            "properties": {"class_name": {"const": cls.__name__}},
                        },
                        {
                            "required": ["name"],
                            "properties": {
                                "name": {"const": cls.__name__},
                                "class_name": {"type": "null"},
                            },
                        },
                    ]
                },
                {
                    "if": {
                        "anyOf": [
                            {"required": ["patterns"]},
                            {"required": ["deny_list"]},
                        ]
                    },
                    "then": {
                        "required": ["type"],
                        "properties": {"type": {"const": "predefined"}},
                    },
                },
            ]
            required = required_constructor_parameters(cls) - {
                "name",
                "supported_language",
            }
            country = getattr(cls, "COUNTRY_CODE", None)
            country_schema: Dict[str, Any] = {"type": "null"}
            if isinstance(country, str):
                country_schema = {
                    "anyOf": [
                        {"type": "null"},
                        {
                            "type": "string",
                            "pattern": r"^\s*"
                            + "".join(
                                f"[{re.escape(char.lower())}{re.escape(char.upper())}]"
                                for char in country
                            )
                            + r"\s*$",
                        },
                    ]
                }
            active: Dict[str, Any] = {
                "required": sorted(
                    required - {"supported_entity", "supported_entities"}
                ),
                "properties": {"country_code": country_schema},
            }
            if required & {"supported_entity", "supported_entities"}:
                active["anyOf"] = [
                    {
                        "required": ["supported_entity"],
                        "properties": {"supported_entity": {"type": "string"}},
                    },
                    {
                        "required": ["supported_entities"],
                        "properties": {
                            "supported_entities": {"type": "array", "minItems": 1}
                        },
                    },
                ]
            entry["allOf"].append(
                {
                    "if": {
                        "not": {
                            "required": ["enabled"],
                            "properties": {"enabled": {"const": False}},
                        }
                    },
                    "then": active,
                }
            )

    bare = {
        "type": "string",
        "enum": [
            cls.__name__
            for cls in classes
            if not (
                required_constructor_parameters(cls) - {"name", "supported_language"}
            )
        ],
    }
    strict_items = {
        "anyOf": [
            bare,
            *[
                {"allOf": [reference], "unevaluatedProperties": False}
                for reference in entry_refs
            ],
        ]
    }
    schema = RecognizerRegistryConfig.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$defs"] = definitions["$defs"]
    schema["required"] = ["recognizers"]
    schema["properties"]["recognizers"] = {
        "type": "array",
        "minItems": 1,
        "items": strict_items if strict else {"anyOf": [bare, *entry_refs]},
    }
    if not strict:
        schema["allOf"] = [
            {
                "if": {
                    "required": ["strict"],
                    "properties": {"strict": {"const": True}},
                },
                "then": {"properties": {"recognizers": {"items": strict_items}}},
            }
        ]
    return schema


def render_recognizer_config_reference(
    recognizer_classes: Optional[Iterable[Type[EntityRecognizer]]] = None,
) -> str:
    """Render a reproducible accepted-key reference without model construction.

    :param recognizer_classes: Additional application-specific recognizer classes.
    :return: Markdown derived from the same constructor models used at runtime.
    """
    classes = _classes(recognizer_classes)
    registry_keys = ", ".join(
        f"`{key}`" for key in sorted(BaseRecognizerConfig.model_fields)
    )
    lines = [
        "# Recognizer configuration key reference",
        "",
        "Generated by `docs/samples/python/generate_recognizer_config_reference.py`.",
        "Do not edit the table by hand; rerun the generator after constructor changes.",
        "",
        f"Registry metadata keys: {registry_keys}.",
        "",
        "The constructor column lists reachable keyword parameters. Omitted settings",
        "keep constructor defaults. Metadata is normalized or validated by registry",
        "rules. `country_code` can tag custom entries; on a predefined entry it must",
        "match the class's declared `COUNTRY_CODE` (omit it on untagged classes).",
        "Required Python",
        "arguments can be supplied by language/entity normalization; use",
        "`validate_registry_config` to validate an actual configuration.",
        "",
        "| Recognizer | Constructor keys | Required constructor arguments |",
        "| --- | --- | --- |",
    ]
    for cls in classes:
        model = derive_config_model(cls)
        keys = sorted(set(constructor_parameters(cls)) & set(model.model_fields))
        required = sorted(required_constructor_parameters(cls))
        lines.append(
            f"| `{cls.__name__}` | {', '.join(f'`{key}`' for key in keys)} | "
            f"{', '.join(f'`{key}`' for key in required) or '-'} |"
        )
    return "\n".join(lines) + "\n"
