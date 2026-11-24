import pytest
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import CaSinRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result_within_score_range


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


@pytest.fixture(scope="module")
def analyzer_from_yaml(tmp_path_factory, spacy_nlp_engine):
    """Analyzer with CaSinRecognizer enabled through registry configuration."""
    conf = tmp_path_factory.mktemp("conf") / "recognizers.yaml"
    conf.write_text(
        """
supported_languages:
  - en
recognizers:
  - name: CaSinRecognizer
    supported_languages:
      - en
    type: predefined
    enabled: true
    country_code: ca
"""
    )
    registry = RecognizerRegistryProvider(conf_file=conf).create_recognizer_registry()
    return AnalyzerEngine(registry=registry, nlp_engine=spacy_nlp_engine)


@pytest.mark.parametrize(
    "text, start, end, expected_score",
    [
        # fmt: off
        # Context phrases raise the score.
        ("My SIN number is 130692544.", 17, 26, 0.4),
        ("Social insurance number 130692544", 24, 33, 0.4),
        ("Social insurance number 130-692-544", 24, 35, 0.85),
        # Context is prefix-only: a phrase after the number does not count.
        ("130692544 is my social insurance number", 0, 9, 0.05),
        # Words containing "sin" or "nas" are not context.
        ("Our business account is 130692544.", 24, 33, 0.05),
        ("Our business account is 130-692-544.", 24, 35, 0.5),
        ("My cousin has account 130692544", 22, 31, 0.05),
        ("The dynasty record 130692544", 19, 28, 0.05),
        # fmt: on
    ],
)
def test_when_enabled_in_yaml_then_context_raises_score_only_for_sin_phrases(
    analyzer_from_yaml, text, start, end, expected_score
):
    results = analyzer_from_yaml.analyze(text, language="en", entities=["CA_SIN"])

    assert [(r.entity_type, r.start, r.end) for r in results] == [
        ("CA_SIN", start, end)
    ]
    assert results[0].score == pytest.approx(expected_score)
