from unittest.mock import Mock
import pandas as pd

import pytest

from presidio_anonymizer.entities import OperatorConfig

from presidio_structured import StructuredEngine
from presidio_structured.data.data_processors import JsonDataProcessor


def test_structured_engine_anonymize_calls_data_processor_operate():
    # Arrange
    data_processor = Mock()
    structured_engine = StructuredEngine(data_processor)
    data = Mock()
    structured_analysis = Mock()
    operators = {"DEFAULT": OperatorConfig("replace")}

    # Act
    structured_engine.anonymize(data, structured_analysis, operators)

    # Assert
    data_processor.operate.assert_called_once_with(data, structured_analysis, operators)


def test_structured_engine_anonymize_adds_default_operator_if_none_provided():
    # Arrange
    data_processor = Mock()
    structured_engine = StructuredEngine(data_processor)
    data = Mock()
    structured_analysis = Mock()

    # Act
    structured_engine.anonymize(data, structured_analysis)

    # Assert
    data_processor.operate.assert_called_once()
    args, _ = data_processor.operate.call_args
    assert "DEFAULT" in args[2]


def test_structured_engine_anonymize_doesnt_override_existing_default_operator():
    # Arrange
    data_processor = Mock()
    structured_engine = StructuredEngine(data_processor)
    data = Mock()
    structured_analysis = Mock()
    operators = {"DEFAULT": OperatorConfig("custom")}

    # Act
    structured_engine.anonymize(data, structured_analysis, operators)

    # Assert
    data_processor.operate.assert_called_once_with(data, structured_analysis, operators)


def test_json_processor_with_pandas_dataframe_will_raise(tabular_analysis):
    data_processor = JsonDataProcessor()
    structured_engine = StructuredEngine(data_processor)
    data = pd.DataFrame({"name": ["John", "Jane"]})
    with pytest.raises(ValueError):
        structured_engine.anonymize(data, tabular_analysis)


def test_pandas_processor_with_json_will_raise(json_analysis):
    structured_engine = StructuredEngine()  # default PandasDataProcessor
    data = {"name": ["John", "Jane"]}
    with pytest.raises(ValueError):
        structured_engine.anonymize(data, json_analysis)


def test_structured_engine_anonymize_does_not_mutate_operators():
    # Arrange
    data_processor = Mock()
    structured_engine = StructuredEngine(data_processor)
    data = Mock()
    structured_analysis = Mock()
    operators = {"PERSON": OperatorConfig("replace")}

    # Act
    structured_engine.anonymize(data, structured_analysis, operators)

    # Assert
    assert "DEFAULT" not in operators
    passed_operators = data_processor.operate.call_args[0][2]
    assert "DEFAULT" in passed_operators
