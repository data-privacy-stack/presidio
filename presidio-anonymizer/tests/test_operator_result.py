import pytest

from presidio_anonymizer.entities import OperatorResult


def test_given_decrypt_result_item_then_all_params_exist():
    result = OperatorResult(0, 3, "NAME", "bla", "decrypt")
    assert result.end == 3
    assert result.start == 0
    assert result.text == "bla"
    assert result.entity_type == "NAME"
    assert result.operator == "decrypt"


def test_given_idenctical_decrypt_results_item_they_are_equal():
    result_1 = OperatorResult(0, 3, "NAME", "bla", "decrypt")
    result_2 = OperatorResult(0, 3, "NAME", "bla", "decrypt")
    assert result_1 == result_2


@pytest.mark.parametrize(
    # fmt: off
    "result_item",
    [
        (OperatorResult(0, 3, "NAME", "bla1", "decrypt")),
        (OperatorResult(0, 3, "NAME", "bla", "decrypt2")),
        (OperatorResult(1, 3, "NAME", "bla", "decrypt")),
        (OperatorResult(0, 4, "NAME", "bla", "decrypt")),
        (OperatorResult(0, 3, "1NAME", "bla", "decrypt")),
    ],
    # fmt: on
)
def test_given_changed_decrypt_results_item_they_are_equal(result_item):
    result_1 = OperatorResult(0, 3, "NAME", "bla", "decrypt")
    assert result_1 != result_item


def test_given_no_score_provided_then_score_defaults_to_none():
    result = OperatorResult(0, 3, "NAME", "bla", "decrypt")
    assert result.score is None


def test_given_score_provided_then_score_is_set():
    result = OperatorResult(0, 3, "NAME", "bla", "decrypt", 0.85)
    assert result.score == 0.85


def test_given_score_provided_as_kwarg_then_score_is_set():
    result = OperatorResult(
        start=0, end=3, entity_type="NAME", text="bla", operator="decrypt", score=0.6
    )
    assert result.score == 0.6


def test_given_two_results_with_different_scores_then_they_are_not_equal():
    result_1 = OperatorResult(0, 3, "NAME", "bla", "decrypt", 0.9)
    result_2 = OperatorResult(0, 3, "NAME", "bla", "decrypt", 0.1)
    assert result_1 != result_2


def test_given_two_results_with_same_score_then_they_are_equal():
    result_1 = OperatorResult(0, 3, "NAME", "bla", "decrypt", 0.9)
    result_2 = OperatorResult(0, 3, "NAME", "bla", "decrypt", 0.9)
    assert result_1 == result_2


def test_given_one_result_has_score_and_other_does_not_then_they_are_not_equal():
    result_1 = OperatorResult(0, 3, "NAME", "bla", "decrypt", 0.9)
    result_2 = OperatorResult(0, 3, "NAME", "bla", "decrypt")
    assert result_1 != result_2


def test_given_result_with_score_then_to_dict_includes_score():
    result = OperatorResult(0, 3, "NAME", "bla", "decrypt", 0.75)
    result_dict = result.to_dict()
    assert result_dict["score"] == 0.75


def test_given_json_with_score_then_from_json_sets_score():
    json_data = {
        "start": 0,
        "end": 10,
        "entity_type": "PERSON",
        "text": "resulted_text",
        "operator": "encrypt",
        "score": 0.85,
    }
    result = OperatorResult.from_json(json_data)
    assert result.score == 0.85


def test_given_json_without_score_then_from_json_defaults_score_to_none():
    json_data = {
        "start": 0,
        "end": 10,
        "entity_type": "PERSON",
        "text": "resulted_text",
        "operator": "encrypt",
    }
    result = OperatorResult.from_json(json_data)
    assert result.score is None
