# ruff: noqa: D103,E501,I001

import random
import time

import pytest

from presidio_analyzer import AnalysisExplanation, EntityRecognizer, RecognizerResult


def _rr(start, end, score, entity_type="x"):
    return RecognizerResult(
        start=start,
        end=end,
        score=score,
        entity_type=entity_type,
        analysis_explanation=AnalysisExplanation(
            recognizer="test",
            original_score=0,
            pattern_name="test",
            pattern="test",
            validation_result=None,
        ),
    )


def _oracle_remove_duplicates(results):
    """Inline O(n^2) replica of the pre-perf-patch remove_duplicates."""
    deduped = sorted(
        list(set(results)), key=lambda x: (-x.score, x.start, -(x.end - x.start))
    )
    filtered = []
    for result in deduped:
        if result.score == 0:
            continue
        to_keep = result not in filtered
        if to_keep:
            for kept in filtered:
                if result.contained_in(kept) and result.entity_type == kept.entity_type:
                    to_keep = False
                    break
        if to_keep:
            filtered.append(result)
    return filtered


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


def test_remove_duplicates_equivalence():
    # contained same-type dropped (higher-score outer kept)
    results = EntityRecognizer.remove_duplicates([_rr(0, 10, 0.9), _rr(2, 5, 0.5)])
    assert [(r.start, r.end, r.score) for r in results] == [(0, 10, 0.9)]

    # contained cross-type kept
    results = EntityRecognizer.remove_duplicates(
        [_rr(0, 10, 0.9, "x"), _rr(2, 5, 0.5, "y")]
    )
    assert len(results) == 2

    # equal-span lower-score dropped
    results = EntityRecognizer.remove_duplicates([_rr(0, 5, 0.9), _rr(0, 5, 0.1)])
    assert len(results) == 1
    assert results[0].score == 0.9

    # score-0 dropped
    results = EntityRecognizer.remove_duplicates([_rr(0, 5, 0.5), _rr(20, 25, 0)])
    assert [(r.start, r.end) for r in results] == [(0, 5)]

    # small deterministic fuzz vs inline O(n^2) oracle
    rng = random.Random(2279)
    for _ in range(50):
        inputs = []
        for _ in range(30):
            start = rng.randint(0, 50)
            end = start + rng.randint(1, 15)
            score = rng.choice([0, 0.1, 0.5, 0.9, 1.0])
            entity_type = rng.choice(["x", "y"])
            inputs.append(_rr(start, end, score, entity_type))
        expected = _oracle_remove_duplicates(inputs)
        actual = EntityRecognizer.remove_duplicates(inputs)
        assert [(r.start, r.end, r.score, r.entity_type) for r in actual] == [
            (r.start, r.end, r.score, r.entity_type) for r in expected
        ]


def test_remove_duplicates_perf_smoke():
    results = [_rr(i * 10, i * 10 + 5, 0.5) for i in range(5000)]
    started = time.perf_counter()
    filtered = EntityRecognizer.remove_duplicates(results)
    elapsed = time.perf_counter() - started
    assert len(filtered) == 5000
    assert elapsed < 2.0


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
