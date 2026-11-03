import pytest
from presidio_analyzer import AnalyzerEngine, EntityRecognizer
from presidio_analyzer.nlp_engine import NlpArtifacts
from presidio_analyzer.predefined_recognizers import NoFodselsnummerRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result
from tests.mocks import NlpEngineMock


@pytest.fixture(scope="module")
def recognizer():
    """Return an instance of the NoFodselsnummerRecognizer."""
    return NoFodselsnummerRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return entities to analyze."""
    return ["NO_FODSELSNUMMER"]


# All numbers are synthetic, built from Skatteetaten's control digit formula.
@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        # Valid fødselsnummer, current control digit rule.
        ("15088500188", 1, ((0, 11),)),
        ("Mitt fødselsnummer er 15088500188.", 1, ((22, 33),)),
        ("150885 00188", 1, ((0, 12),)),
        # Valid under the control digit rule for numbers issued from 2032.
        ("01013300085", 1, ((0, 11),)),
        ("01013300093", 1, ((0, 11),)),
        ("01013300182", 1, ((0, 11),)),
        # D-nummer (day + 40), H-nummer (month + 40), Tenor synthetic (month + 80).
        ("D-nummer: 42079000056", 1, ((10, 21),)),
        ("01419000066", 1, ((0, 11),)),
        ("01819000049", 1, ((0, 11),)),
        # 29 February in a leap year.
        ("29020000064", 1, ((0, 11),)),
        # Invalid: wrong second control digit.
        ("15088500189", 0, ()),
        # Invalid: first control digit outside both rules.
        ("15088500110", 0, ()),
        # Invalid: 30 February, although both control digits match.
        ("30029000057", 0, ()),
        # Lookalike: a valid Norwegian bank account number (same length, mod 11).
        ("Kontonummer 12345678903", 0, ()),
        # Invalid: part of a longer number, or not all digits.
        ("150885001881", 0, ()),
        ("1508850018x", 0, ()),
    ],
)
def test_when_all_norwegian_fodselsnummer_then_succeed(
    text, expected_len, expected_positions, recognizer, entities, max_score
):
    """Tests our recognizer against valid & invalid Norwegian fødselsnummer."""
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, max_score)


class _NorwegianNlpEngineMock(NlpEngineMock):
    def __init__(self):
        super().__init__(nlp_artifacts=NlpArtifacts([], [], [], [], None, "nb", []))

    def get_supported_languages(self):
        return ["nb"]


def test_when_enabled_in_yaml_then_loads_and_detects(tmp_path):
    """Detection must work through the path users actually configure.

    The recognizer is Norwegian only, so the top-level supported_languages
    must include "nb" or the registry filters it out silently.
    """
    conf = tmp_path / "recognizers.yaml"
    conf.write_text(
        """
supported_languages:
  - nb
recognizers:
  - name: NoFodselsnummerRecognizer
    supported_languages:
      - nb
    type: predefined
    enabled: true
    country_code: "no"
"""
    )
    registry = RecognizerRegistryProvider(conf_file=conf).create_recognizer_registry()
    analyzer = AnalyzerEngine(
        registry=registry,
        nlp_engine=_NorwegianNlpEngineMock(),
        supported_languages=["nb"],
    )

    text = "Fødselsnummer 15088500188"
    results = analyzer.analyze(text, language="nb")

    assert [(r.entity_type, r.start, r.end) for r in results] == [
        ("NO_FODSELSNUMMER", 14, 25)
    ]
    assert results[0].score == pytest.approx(EntityRecognizer.MAX_SCORE)


def test_when_number_is_valid_then_score_is_max_with_or_without_context(
    recognizer, entities
):
    """Context does not change the score of a validated number.

    Every reported match has passed the date and both control digits, so
    validate_result sets it to MAX_SCORE and context cannot raise it further.
    Invalid numbers are dropped, so context never rescues them either.
    """
    with_context = recognizer.analyze("Fødselsnummer 15088500188", entities)
    without_context = recognizer.analyze("Kode 15088500188", entities)

    assert with_context[0].score == pytest.approx(EntityRecognizer.MAX_SCORE)
    assert without_context[0].score == pytest.approx(EntityRecognizer.MAX_SCORE)
    assert recognizer.analyze("Fødselsnummer 15088500189", entities) == []
