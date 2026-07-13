from presidio_analyzer import EntityRecognizer, RecognizerResult, AnalysisExplanation


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

import pytest


# ---------------------------------------------------------------------------
# merge_adjacent_text_entities tests
# ---------------------------------------------------------------------------

def test_merge_adjacent_same_type_entities():
    """Two PERSON spans separated by a single space are merged into one."""
    text = "My name is Dave Jones"
    results = [
        RecognizerResult(entity_type="PERSON", start=11, end=15, score=0.85),
        RecognizerResult(entity_type="PERSON", start=16, end=21, score=0.85),
    ]
    merged = EntityRecognizer.merge_adjacent_text_entities(results, text)
    assert len(merged) == 1
    assert merged[0].start == 11
    assert merged[0].end == 21
    assert merged[0].entity_type == "PERSON"


def test_merge_adjacent_preserves_max_score():
    """Merged entity takes the higher of the two scores."""
    text = "Anne Marie"
    results = [
        RecognizerResult(entity_type="PERSON", start=0, end=4, score=0.7),
        RecognizerResult(entity_type="PERSON", start=5, end=10, score=0.9),
    ]
    merged = EntityRecognizer.merge_adjacent_text_entities(results, text)
    assert len(merged) == 1
    assert merged[0].score == 0.9


def test_merge_adjacent_three_tokens():
    """Three consecutive same-type spans are merged into a single result."""
    text = "Jean Luc Picard"
    results = [
        RecognizerResult(entity_type="PERSON", start=0, end=4, score=0.8),
        RecognizerResult(entity_type="PERSON", start=5, end=8, score=0.8),
        RecognizerResult(entity_type="PERSON", start=9, end=15, score=0.8),
    ]
    merged = EntityRecognizer.merge_adjacent_text_entities(results, text)
    assert len(merged) == 1
    assert merged[0].start == 0
    assert merged[0].end == 15


def test_no_merge_when_different_entity_types():
    """Adjacent spans of different types are NOT merged."""
    text = "John London"
    results = [
        RecognizerResult(entity_type="PERSON", start=0, end=4, score=0.8),
        RecognizerResult(entity_type="LOCATION", start=5, end=11, score=0.8),
    ]
    merged = EntityRecognizer.merge_adjacent_text_entities(results, text)
    assert len(merged) == 2


def test_no_merge_when_gap_has_non_whitespace():
    """Spans separated by non-whitespace characters are NOT merged."""
    text = "foo, bar"
    results = [
        RecognizerResult(entity_type="PERSON", start=0, end=3, score=0.8),
        RecognizerResult(entity_type="PERSON", start=5, end=8, score=0.8),
    ]
    merged = EntityRecognizer.merge_adjacent_text_entities(results, text)
    assert len(merged) == 2


def test_merge_empty_results():
    """Empty input returns empty output without error."""
    merged = EntityRecognizer.merge_adjacent_text_entities([], "some text")
    assert merged == []


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
