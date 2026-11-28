from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.predefined_recognizers import CaSinRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result_within_score_range


@pytest.fixture(scope="module")
def analyzer(spacy_nlp_engine):
    """AnalyzerEngine with only CaSinRecognizer, as in issue #2459."""
    registry = RecognizerRegistry()
    registry.add_recognizer(CaSinRecognizer())
    return AnalyzerEngine(
        registry=registry, nlp_engine=spacy_nlp_engine, supported_languages=["en"]
    )


@pytest.fixture(scope="module")
def recognizer():
    return CaSinRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["CA_SIN"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # --- Valid SINs ---
        # Space delimited
        ("130 692 544", 1, ((0, 11),), ((0.5, 0.81),),),
        ("435 418 165", 1, ((0, 11),), ((0.5, 0.81),),),
        ("948 584 792", 1, ((0, 11),), ((0.5, 0.81),),),
        # Hyphen delimited
        ("347-677-452", 1, ((0, 11),), ((0.5, 0.81),),),
        ("731-530-150", 1, ((0, 11),), ((0.5, 0.81),),),
        # No delimiter
        ("130692544", 1, ((0, 9),), ((0.0, 0.3),),),
        ("550090112", 1, ((0, 9),), ((0.0, 0.3),),),

        # --- Valid SIN with context ---
        ("my SIN is 130-692-544", 1, ((10, 21),), ((0.5, 0.81),),),
        ("mon NAS: 258 933 688", 1, ((9, 20),), ((0.5, 0.81),),),

        # --- Invalid: checksum failure ---
        ("130 692 545", 0, (), (),),
        ("130692545", 0, (), (),),
        ("435-418-166", 0, (), (),),

        # --- Invalid: reserved first digit ---
        ("046 454 286", 0, (), (),),
        ("812 345 678", 0, (), (),),

        # --- Invalid: all same digit ---
        ("111 111 111", 0, (), (),),
        ("999 999 999", 0, (), (),),

        # --- Invalid: mismatched delimiters ---
        ("046-454 286", 0, (), (),),
        ("046 454-286", 0, (), (),),

        # --- Invalid: wrong length ---
        ("13069254", 0, (), (),),
        ("1306925440", 0, (), (),),
        # fmt: on
    ],
)
def test_when_sin_in_text_then_all_ca_sins_are_found(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    results = recognizer.analyze(text, entities)
    results = sorted(results, key=lambda x: x.start)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        if fn_score == "max":
            fn_score = max_score
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )


@pytest.mark.parametrize(
    "text, expected_positions, expected_scores",
    [
        # fmt: off
        # "sin" inside "business" must not boost the score (#2459)
        ("Our business account is 130-692-544.", ((24, 35),), ((0.5, ""),),),
        ("Our business account is 130692544.", ((24, 33),), ((0.05, ""),),),
        # Other words containing "sin" must not boost either
        ("My cousin's number is 130-692-544.", ((22, 33),), ((0.5, ""),),),
        ("My single account is 130-692-544.", ((21, 32),), ((0.5, ""),),),
        # The token "sin" itself still boosts
        ("My SIN is 130-692-544.", ((10, 21),), ((0.85, "sin"),),),
        ("My SIN is 130692544.", ((10, 19),), ((0.4, "sin"),),),
        # Longer context words still boost
        (
            "My social insurance number is 130-692-544.",
            ((30, 41),),
            ((0.85, "social insurance"),),
        ),
        ("Mon NAS est 130-692-544.", ((12, 23),), ((0.85, "nas"),),),
        # fmt: on
    ],
)
def test_context_word_sin_matches_whole_token_only(
    text, expected_positions, expected_scores, analyzer
):
    """Context word "sin" must match the token "sin" only, not substrings.

    Regression test for #2459: with the default substring matching,
    "business", "cousin" and "single" all boosted unrelated 9-digit
    numbers to 0.85 / 0.4 as if "SIN" were next to them.
    """
    results = analyzer.analyze(
        text=text,
        language="en",
        entities=["CA_SIN"],
        return_decision_process=True,
    )
    assert len(results) == len(expected_scores)
    for res, (st_pos, fn_pos), (score, word) in zip(
        results, expected_positions, expected_scores
    ):
        assert res.entity_type == "CA_SIN"
        assert (res.start, res.end) == (st_pos, fn_pos)
        assert res.score == score
        assert res.analysis_explanation.supportive_context_word == word


def test_loads_from_default_recognizers_yaml(spacy_nlp_engine):
    """Recognizer loads from the shipped YAML and keeps whole-word matching.

    The configuration path is how users enable this recognizer, so the
    #2459 fix must hold there too, not only when built in Python.
    """
    conf = (
        Path(presidio_analyzer.__file__).parent
        / "conf"
        / "default_recognizers.yaml"
    )
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "CaSinRecognizer"]
    assert len(entries) == 1, "CaSinRecognizer missing from YAML"
    entry = entries[0]
    assert entry["country_code"] == "ca"
    assert "en" in entry["supported_languages"]

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()
    assert [type(r).__name__ for r in registry.recognizers] == ["CaSinRecognizer"]

    analyzer = AnalyzerEngine(
        registry=registry, nlp_engine=spacy_nlp_engine, supported_languages=["en"]
    )
    business = analyzer.analyze(
        text="Our business account is 130-692-544.",
        language="en",
        entities=["CA_SIN"],
        return_decision_process=True,
    )
    assert [
        (r.score, r.analysis_explanation.supportive_context_word)
        for r in business
    ] == [(0.5, "")]
    sin = analyzer.analyze(
        text="My SIN is 130-692-544.",
        language="en",
        entities=["CA_SIN"],
        return_decision_process=True,
    )
    assert [
        (r.score, r.analysis_explanation.supportive_context_word) for r in sin
    ] == [(0.85, "sin")]
