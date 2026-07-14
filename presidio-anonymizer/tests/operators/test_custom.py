import pytest

from presidio_anonymizer.operators import Custom
from presidio_anonymizer.entities import InvalidParamError


def test_given_non_callable_for_custom_then_ipe_raised():
    with pytest.raises(
        InvalidParamError,
        match="New value must be a callable function",
    ):
        Custom().validate({"lambda": "bla"})


def test_given_lambda_for_custom_we_get_the_result_back():
    text = Custom().operate("bla", {"lambda": lambda x: x[::-1]})
    assert text == "alb"


def test_given_non_str_lambda_then_ipe_raised_at_operate_time():
    """Non-str return type is caught in operate(), not validate().

    Previously validate() called the lambda with 'PII' to check the return
    type, which caused side effects in stateful lambdas (see #2024).
    The return-type contract is now enforced in operate() on real data.
    """
    with pytest.raises(InvalidParamError):
        Custom().operate("hello", {"lambda": lambda x: len(x)})


def test_stateful_lambda_not_called_during_validate():
    """validate() must not invoke the lambda — stateful lambdas must not
    observe a spurious call with a dummy value.

    Regression test for https://github.com/data-privacy-stack/presidio/issues/2024.
    Before the fix, validate() called the lambda with 'PII', causing stateful
    lambdas to insert a spurious {'TOKEN_1': 'PII'} entry into their token map
    and shifting all subsequent token counters by one.
    """
    call_log = []

    def stateful_lambda(value: str) -> str:
        call_log.append(value)
        return f"[TOKEN_{len(call_log)}]"

    Custom().validate({"lambda": stateful_lambda})

    assert call_log == [], (
        "validate() must not call the lambda — "
        f"but it was called with: {call_log}"
    )


def test_stateful_token_map_not_corrupted_by_validate():
    """Token map built by a stateful lambda must contain only real values,
    not the dummy 'PII' string injected during validation.

    Regression test for https://github.com/data-privacy-stack/presidio/issues/2024.
    """
    token_map = {}
    counter = {"n": 0}

    def build_map(value: str) -> str:
        counter["n"] += 1
        token = f"PERSON_{counter['n']}"
        token_map[token] = value
        return f"[{token}]"

    Custom().validate({"lambda": build_map})
    Custom().operate("Alice", {"lambda": build_map})
    Custom().operate("Bob", {"lambda": build_map})

    assert "PII" not in token_map.values(), (
        f"token_map contains spurious 'PII' entry: {token_map}"
    )
    assert token_map == {"PERSON_1": "Alice", "PERSON_2": "Bob"}


def test_when_validate_anonymizer_then_correct_name():
    assert Custom().operator_name() == "custom"
