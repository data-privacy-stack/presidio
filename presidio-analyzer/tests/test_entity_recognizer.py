# ruff: noqa: D103,E501,I001

import pytest

from presidio_analyzer import AnalysisExplanation, EntityRecognizer, RecognizerResult


def test_when_to_dict_then_return_correct_dictionary():
    ent_recognizer = EntityRecognizer(["ENTITY"])
    entity_rec_dict = ent_recognizer.to_dict()

    assert entity_rec_dict is not None
    assert entity_rec_dict["supported_entities"] == ["ENTITY"]
    assert entity_rec_dict["supported_language"] == "en"


def test_when_from_dict_then_returns_instance():
    ent_rec_dict = {"supported_entities": ["A", "B", "C"], "supported_language": "he"}
    entity_rec = EntityRecognizer.from_dict(ent_rec_dict)

    assert entity_rec.supported_entities == ["A", "B", "C"]
    assert entity_rec.supported_language == "he"
    assert entity_rec.version == "0.0.1"


def test_when_remove_duplicates_duplicates_removed():
    # test same result with different score will return only the highest
    arr = [
        RecognizerResult(
            start=0,
            end=5,
            score=0.1,
            entity_type="x",
            analysis_explanation=AnalysisExplanation(
                recognizer="test",
                original_score=0,
                pattern_name="test",
                pattern="test",
                validation_result=None,
            ),
        ),
        RecognizerResult(
            start=0,
            end=5,
            score=0.5,
            entity_type="x",
            analysis_explanation=AnalysisExplanation(
                recognizer="test",
                original_score=0,
                pattern_name="test",
                pattern="test",
                validation_result=None,
            ),
        ),
    ]
    results = EntityRecognizer.remove_duplicates(arr)
    assert len(results) == 1
    assert results[0].score == 0.5


def test_when_remove_duplicates_different_then_entity_not_removed():
    # test same result with different score will return only the highest
    arr = [
        RecognizerResult(
            start=0,
            end=5,
            score=0.1,
            entity_type="x",
            analysis_explanation=AnalysisExplanation(
                recognizer="test",
                original_score=0,
                pattern_name="test",
                pattern="test",
                validation_result=None,
            ),
        ),
        RecognizerResult(
            start=0,
            end=5,
            score=0.5,
            entity_type="y",
            analysis_explanation=AnalysisExplanation(
                recognizer="test",
                original_score=0,
                pattern_name="test",
                pattern="test",
                validation_result=None,
            ),
        ),
    ]
    results = EntityRecognizer.remove_duplicates(arr)
    assert len(results) == 2


def test_when_remove_duplicates_contained_shorter_length_results_removed():
    arr = [
        RecognizerResult(
            start=0,
            end=10,
            score=0.5,
            entity_type="x",
            analysis_explanation=AnalysisExplanation(
                recognizer="test",
                original_score=0,
                pattern_name="test",
                pattern="test",
                validation_result=None,
            ),
        ),
        RecognizerResult(
            start=0,
            end=5,
            score=0.5,
            entity_type="x",
            analysis_explanation=AnalysisExplanation(
                recognizer="test",
                original_score=0,
                pattern_name="test",
                pattern="test",
                validation_result=None,
            ),
        ),
    ]
    results = EntityRecognizer.remove_duplicates(arr)
    assert len(results) == 1

sanitizer_test_set = [
    ["  a|b:c       ::-", [("-", ""), (" ", ""), (":", ""), ("|", "")], "abc"],
    ["def", "", "def"],
]

@pytest.mark.parametrize("input_text, params, expected_output", sanitizer_test_set)
def test_sanitize_value(input_text, params, expected_output):
    """
    Test to assert sanitize_value functionality from base class.

    :param input_text: input string
    :param params: List of tuples, indicating what has to be sanitized with which
    :param expected_output: sanitized value
    :return: True/False
    """
    assert EntityRecognizer.sanitize_value(input_text, params) == expected_output


def test_score_thresholds_default_to_empty_mapping():
    recognizer = EntityRecognizer(["ENTITY"])

    assert recognizer.score_thresholds == {}


def test_score_thresholds_constructor_and_setter_defensively_copy():
    thresholds = {"default": 0.4, "ENTITY": 0.7}
    recognizer = EntityRecognizer(["ENTITY"], score_thresholds=thresholds)
    thresholds["ENTITY"] = 0.1
    returned = recognizer.score_thresholds
    returned["ENTITY"] = 0.2

    assert recognizer.score_thresholds == {"default": 0.4, "ENTITY": 0.7}

    recognizer.score_thresholds = {"ENTITY": 0.5}
    assert recognizer.score_thresholds == {"ENTITY": 0.5}


@pytest.mark.parametrize("thresholds", [False, True, 0, "", "0.4", []])
def test_score_thresholds_reject_non_mapping_values(thresholds):
    with pytest.raises(ValueError, match="must be a mapping"):
        EntityRecognizer(["ENTITY"], score_thresholds=thresholds)


@pytest.mark.parametrize(
    "thresholds",
    [
        {"ENTITY": False},
        {"ENTITY": "0.4"},
        {"ENTITY": -0.1},
        {"ENTITY": 1.1},
        {"": 0.4},
        {" ENTITY": 0.4},
    ],
)
def test_score_thresholds_reject_invalid_entries(thresholds):
    with pytest.raises(ValueError):
        EntityRecognizer(["ENTITY"], score_thresholds=thresholds)


def _result(entity_type, start, end, score):
    return RecognizerResult(entity_type=entity_type, start=start, end=end, score=score)


def test_when_merge_adjacent_same_type_entities_then_merged():
    text = "My name is Dave Jones and I live in Texas"
    dave = _result("PERSON", 11, 15, 0.6)
    jones = _result("PERSON", 16, 21, 0.85)

    merged = EntityRecognizer.merge_adjacent_text_entities(
        [dave, jones], text, entity_types=["PERSON"]
    )

    assert len(merged) == 1
    assert merged[0].start == 11
    assert merged[0].end == 21
    assert merged[0].score == 0.85


def test_when_merge_preserves_winning_metadata():
    text = "Dave Jones"
    explanation_low = AnalysisExplanation(
        recognizer="low",
        original_score=0.6,
        pattern_name="low",
        pattern="low",
        validation_result=None,
    )
    explanation_high = AnalysisExplanation(
        recognizer="high",
        original_score=0.85,
        pattern_name="high",
        pattern="high",
        validation_result=None,
    )
    dave = RecognizerResult(
        entity_type="PERSON",
        start=0,
        end=4,
        score=0.6,
        analysis_explanation=explanation_low,
        recognition_metadata={"recognizer_identifier": "low"},
    )
    jones = RecognizerResult(
        entity_type="PERSON",
        start=5,
        end=10,
        score=0.85,
        analysis_explanation=explanation_high,
        recognition_metadata={"recognizer_identifier": "high"},
    )

    merged = EntityRecognizer.merge_adjacent_text_entities(
        [dave, jones], text, entity_types=["PERSON"]
    )

    assert len(merged) == 1
    assert merged[0].score == 0.85
    assert merged[0].analysis_explanation == explanation_high
    assert merged[0].recognition_metadata == {"recognizer_identifier": "high"}


def test_when_merge_three_adjacent_tokens_then_collapse_to_one():
    text = "Jean Luc Picard"
    jean = _result("PERSON", 0, 4, 0.5)
    luc = _result("PERSON", 5, 8, 0.5)
    picard = _result("PERSON", 9, 15, 0.9)

    merged = EntityRecognizer.merge_adjacent_text_entities(
        [picard, jean, luc], text, entity_types=["PERSON"]
    )

    assert len(merged) == 1
    assert merged[0].start == 0
    assert merged[0].end == 15
    assert merged[0].score == 0.9


def test_when_different_entity_types_then_not_merged():
    text = "Dave Texas"
    dave = _result("PERSON", 0, 4, 0.6)
    texas = _result("LOCATION", 5, 10, 0.6)

    merged = EntityRecognizer.merge_adjacent_text_entities(
        [dave, texas], text, entity_types=["PERSON", "LOCATION"]
    )

    assert len(merged) == 2


def test_when_gap_has_non_whitespace_then_not_merged():
    text = "Dave, Jones"
    dave = _result("PERSON", 0, 4, 0.6)
    jones = _result("PERSON", 6, 11, 0.6)

    merged = EntityRecognizer.merge_adjacent_text_entities(
        [dave, jones], text, entity_types=["PERSON"]
    )

    assert len(merged) == 2


def test_when_entity_type_not_in_eligible_list_then_not_merged():
    text = "Dave Jones"
    dave = _result("PERSON", 0, 4, 0.6)
    jones = _result("PERSON", 5, 10, 0.6)

    merged = EntityRecognizer.merge_adjacent_text_entities(
        [dave, jones], text, entity_types=["LOCATION"]
    )

    assert len(merged) == 2


def test_when_entity_types_none_then_no_merging_by_default():
    text = "Dave Jones"
    dave = _result("PERSON", 0, 4, 0.6)
    jones = _result("PERSON", 5, 10, 0.6)

    merged = EntityRecognizer.merge_adjacent_text_entities([dave, jones], text)

    assert len(merged) == 2


def test_when_overlapping_spans_then_not_merged():
    text = "Dave Jones"
    dave = _result("PERSON", 0, 6, 0.6)  # overlaps into "Jo"
    jones = _result("PERSON", 5, 10, 0.7)

    merged = EntityRecognizer.merge_adjacent_text_entities(
        [dave, jones], text, entity_types=["PERSON"]
    )

    assert len(merged) == 2


def test_when_unsorted_input_then_still_merges_correctly():
    text = "Dave Jones"
    dave = _result("PERSON", 0, 4, 0.6)
    jones = _result("PERSON", 5, 10, 0.7)

    merged = EntityRecognizer.merge_adjacent_text_entities(
        [jones, dave], text, entity_types=["PERSON"]
    )

    assert len(merged) == 1
    assert merged[0].start == 0
    assert merged[0].end == 10


def test_when_empty_results_then_empty_output():
    merged = EntityRecognizer.merge_adjacent_text_entities([], "some text")
    assert merged == []
