import pytest

from presidio_anonymizer.entities import InvalidParamError, OperatorConfig


def test_given_valid_json_then_we_parse_it_to_operator_config():
    operator_config = OperatorConfig.from_json(
        {"type": "mask", "masking_char": "*", "chars_to_mask": 4, "from_end": True}
    )
    assert operator_config.operator_name == "mask"
    assert operator_config.params == {
        "masking_char": "*",
        "chars_to_mask": 4,
        "from_end": True,
    }


def test_given_valid_json_then_from_json_leaves_input_unchanged():
    params = {
        "type": "mask",
        "masking_char": "*",
        "chars_to_mask": 4,
        "from_end": True,
    }
    original = dict(params)

    OperatorConfig.from_json(params)

    assert params == original
    assert params["type"] == "mask"


def test_given_same_json_then_from_json_can_be_called_twice():
    params = {"type": "replace", "new_value": "REDACTED"}
    original = dict(params)

    first = OperatorConfig.from_json(params)
    second = OperatorConfig.from_json(params)

    assert first == second
    assert params == original


def test_given_invalid_json_then_we_fail_to_parse_it_to_operator_config():
    expected_error = "Invalid input, operator config must contain operator_name"
    with pytest.raises(InvalidParamError, match=expected_error):
        OperatorConfig.from_json(
            {"masking_char": "*", "chars_to_mask": 4, "from_end": True}
        )


def test_given_two_identical_entities_then_we_verify_they_are_equal():
    one = OperatorConfig("name", {"key", "key"})
    two = OperatorConfig("name", {"key", "key"})
    assert one == two


@pytest.mark.parametrize(
    # fmt: off
    "anonymizer_config",
    [
        OperatorConfig("name1", {"key", "key"}),
        OperatorConfig("name1", {}),
    ],
    # fmt: on
)
def test_given_two_different_entities_then_we_verify_they_are_equal(anonymizer_config):
    one = OperatorConfig("name", {"key", "key"})
    assert one != anonymizer_config


@pytest.mark.parametrize(
    # fmt: off
    "class_name",
    [
        "hash", "mask", "redact", "replace"
    ],
    # fmt: on
)
def test_given_json_then_anonymizer_config_is_created_properly(class_name):
    json = {"type": class_name, "param_1": "my_parameter"}
    operator_config = OperatorConfig.from_json(json)
    assert operator_config.operator_name == class_name
    assert operator_config.params == {"param_1": "my_parameter"}
