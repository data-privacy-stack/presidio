"""Test the data processors' operator mapping."""

import pandas as pd
import pytest
from presidio_anonymizer.entities import InvalidParamError, OperatorConfig

from presidio_structured import StructuredAnalysis, StructuredEngine
from presidio_structured.data.data_processors import (
    JsonDataProcessor,
    PandasDataProcessor,
)


@pytest.fixture
def analysis():
    return StructuredAnalysis(
        entity_mapping={"name": "PERSON", "city": "LOCATION"}
    )


@pytest.fixture
def df():
    return pd.DataFrame({"name": ["John Doe"], "city": ["Anytown"]})


@pytest.fixture
def json_data():
    return {"name": "John Doe", "city": "Anytown"}


def test_default_operator_replaces_with_the_entity_type(analysis, df):
    """The default ``replace`` operator names the entity, as it does for text."""
    result = StructuredEngine().anonymize(df, analysis)

    assert result["name"][0] == "<PERSON>"
    assert result["city"][0] == "<LOCATION>"


def test_default_operator_replaces_with_the_entity_type_in_json(analysis, json_data):
    """Same for the JSON processor."""
    result = StructuredEngine(data_processor=JsonDataProcessor()).anonymize(
        json_data, analysis
    )

    assert result == {"name": "<PERSON>", "city": "<LOCATION>"}


def test_entity_without_a_specific_operator_falls_back_to_default(analysis, df):
    """An entity not named in ``operators`` uses DEFAULT and still gets its type."""
    operators = {"PERSON": OperatorConfig("replace", {"new_value": "REDACTED"})}

    result = StructuredEngine().anonymize(df, analysis, operators)

    assert result["name"][0] == "REDACTED"
    assert result["city"][0] == "<LOCATION>"


def test_explicit_new_value_takes_precedence_over_the_entity_type(analysis, df):
    """An explicit ``new_value`` is unaffected by the added entity type."""
    operators = {"DEFAULT": OperatorConfig("replace", {"new_value": "ANONYMIZED"})}

    result = StructuredEngine().anonymize(df, analysis, operators)

    assert list(result["name"]) == ["ANONYMIZED"]
    assert list(result["city"]) == ["ANONYMIZED"]


def test_operator_config_params_are_not_mutated(analysis, df):
    """The entity type is added to a copy, so a reused config stays clean."""
    config = OperatorConfig("replace", {"new_value": "ANONYMIZED"})

    StructuredEngine().anonymize(df, analysis, {"DEFAULT": config})

    assert config.params == {"new_value": "ANONYMIZED"}


@pytest.mark.parametrize(
    "operator_config, expected_message",
    [
        (
            OperatorConfig("mask", {"masking_char": "*"}),
            "Expected parameter chars_to_mask",
        ),
        (
            OperatorConfig("mask", {"masking_char": "**", "chars_to_mask": 2, "from_end": False}),
            "masking_char must be a character",
        ),
        (
            OperatorConfig("encrypt", {"key": "short"}),
            "key must be of length 128, 192 or 256 bits",
        ),
        (
            OperatorConfig("hash", {"hash_type": "md5"}),
            "hash_type",
        ),
    ],
)
def test_invalid_operator_params_raise_an_actionable_error(
    operator_config, expected_message, analysis, df
):
    """Invalid parameters are reported before any data is processed."""
    operators = {"PERSON": operator_config, "LOCATION": OperatorConfig("redact")}

    with pytest.raises(InvalidParamError, match=expected_message):
        StructuredEngine().anonymize(df, analysis, operators)


def test_invalid_operator_params_are_rejected_before_touching_the_data(analysis, df):
    """Validation happens while building the mapping, so data stays untouched."""
    operators = {"PERSON": OperatorConfig("mask", {"masking_char": "*"})}

    with pytest.raises(InvalidParamError):
        StructuredEngine().anonymize(df, analysis, operators)

    assert df["name"][0] == "John Doe"
    assert df["city"][0] == "Anytown"


@pytest.mark.parametrize(
    "operator_name, expected",
    [
        ("redact", ""),
        ("keep", "John Doe"),
    ],
)
def test_operators_that_ignore_the_entity_type_are_unaffected(
    operator_name, expected, df
):
    """Operators which do not read ``entity_type`` keep working as before."""
    analysis = StructuredAnalysis(entity_mapping={"name": "PERSON"})

    result = StructuredEngine().anonymize(
        df, analysis, {"PERSON": OperatorConfig(operator_name)}
    )

    assert result["name"][0] == expected


def test_custom_operator_receives_the_text_only(df):
    """The ``custom`` operator's lambda is unaffected by the added parameter."""
    analysis = StructuredAnalysis(entity_mapping={"name": "PERSON"})
    operators = {"PERSON": OperatorConfig("custom", {"lambda": lambda x: x.upper()})}

    result = StructuredEngine().anonymize(df, analysis, operators)

    assert result["name"][0] == "JOHN DOE"


def test_entity_without_an_operator_or_default_raises(analysis):
    """An unmapped entity with no DEFAULT is still reported as before."""
    processor = PandasDataProcessor()

    with pytest.raises(ValueError, match="Operator for entity LOCATION not found"):
        processor._generate_operator_mapping(
            analysis, {"PERSON": OperatorConfig("redact")}
        )


def test_generate_operator_mapping_passes_the_entity_type(analysis):
    """The mapping itself carries the entity type into the operator params."""
    processor = PandasDataProcessor()

    mapping = processor._generate_operator_mapping(
        analysis, {"DEFAULT": OperatorConfig("replace")}
    )

    assert mapping["name"]("John Doe") == "<PERSON>"
    assert mapping["city"]("Anytown") == "<LOCATION>"
