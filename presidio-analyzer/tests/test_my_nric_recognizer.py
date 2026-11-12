from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import MyNricRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result

# All MyKad numbers below are synthetic: they follow the published structure
# (YYMMDD-PB-###G) but were made up for these tests.


@pytest.fixture(scope="module")
def recognizer():
    return MyNricRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["MY_NRIC"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_scores",
    [
        # fmt: off
        # Valid, with dashes (state code 14 = Kuala Lumpur)
        ("900101-14-5678", 1, ((0, 14),), (0.4,)),
        # Valid, without dashes (state code 08 = Perak)
        ("850512085123", 1, ((0, 12),), (0.1,)),
        # Valid leap day in a two-digit year (2000 was a leap year)
        ("000229-10-1235", 1, ((0, 14),), (0.4,)),
        # Valid foreign-born codes: 60 (Brunei), 71 (abroad), 98 (stateless)
        ("770315-60-0012", 1, ((0, 14),), (0.4,)),
        ("770315711234", 1, ((0, 12),), (0.1,)),
        ("770315-98-0013", 1, ((0, 14),), (0.4,)),
        # Embedded in text
        ("Applicant 880808-01-4321 signed the form.", 1, ((10, 24),), (0.4,)),
        ("ref 030417591236 end", 1, ((4, 16),), (0.1,)),
        # Two numbers in one text
        ("900101-14-5678 and 850512085123", 2, ((0, 14), (19, 31),), (0.4, 0.1)),
        # Invalid month
        ("901301-14-5678", 0, (), ()),
        ("900001145678", 0, (), ()),
        # Invalid day
        ("900132-14-5678", 0, (), ()),
        ("900230145678", 0, (), ()),
        ("010229-10-1235", 0, (), ()),
        # Unassigned place-of-birth codes
        ("900101-00-5678", 0, (), ()),
        ("900101-17-5678", 0, (), ()),
        ("900101205678", 0, (), ()),
        ("900101-69-5678", 0, (), ()),
        ("900101-73-5678", 0, (), ()),
        ("900101-80-5678", 0, (), ()),
        ("900101-95-5678", 0, (), ()),
        # Same shape, not a MyKad: a 12-digit order number with no valid date
        ("Order 202499887766 shipped", 0, (), ()),
        # Wrong length or grouping
        ("90010114567", 0, (), ()),
        ("9001011456789", 0, (), ()),
        ("9001-0114-5678", 0, (), ()),
        ("AB900101145678", 0, (), ()),
        # fmt: on
    ],
)
def test_when_mykad_in_text_then_detected_with_exact_score(
    text, expected_len, expected_positions, expected_scores, recognizer, entities
):
    results = sorted(recognizer.analyze(text, entities), key=lambda r: r.start)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos), score in zip(
        results, expected_positions, expected_scores
    ):
        assert_result(res, entities[0], st_pos, fn_pos, score)


@pytest.mark.parametrize(
    "pattern_text, expected",
    [
        ("900101-14-5678", False),
        ("900101145678", False),
        ("991231-99-9999", False),
        ("010101-16-0000", False),
        ("010101-21-0000", False),
        ("010101-59-0000", False),
        ("010101-82-0000", False),
        ("010101-93-0000", False),
        ("901301145678", True),
        ("900100145678", True),
        ("900101185678", True),
        ("900101975678", True),
        ("90010114567", True),
        ("90010114567X", True),
    ],
)
def test_invalidate_result(pattern_text, expected, recognizer):
    assert recognizer.invalidate_result(pattern_text) is expected


def test_place_of_birth_codes_match_published_ranges():
    expected = (
        set(range(1, 17))
        | set(range(21, 60))
        | set(range(60, 69))
        | {71, 72}
        | set(range(74, 80))
        | set(range(82, 94))
        | {98, 99}
    )
    assert {int(c) for c in MyNricRecognizer.VALID_PLACE_OF_BIRTH_CODES} == expected


@pytest.fixture(scope="module")
def analyzer(spacy_nlp_engine):
    analyzer = AnalyzerEngine(nlp_engine=spacy_nlp_engine, supported_languages=["en"])
    analyzer.registry.add_recognizer(MyNricRecognizer())
    return analyzer


@pytest.mark.parametrize(
    "text, expected_start, expected_end, expected_score",
    [
        # fmt: off
        # No context: pattern score only
        ("The number is 850512085123", 14, 26, 0.1),
        ("The number is 900101-14-5678", 14, 28, 0.4),
        # Context words before the number raise the score by 0.35
        ("My MyKad number is 850512085123", 19, 31, 0.45),
        ("NRIC 900101145678", 5, 17, 0.45),
        ("IC no. 900101-14-5678", 7, 21, 0.75),
        ("No. K/P: 900101-14-5678", 9, 23, 0.75),
        ("Kad Pengenalan 900101-14-5678", 15, 29, 0.75),
        # Words that merely contain "ic" do not count as context
        ("Applicant 900101-14-5678", 10, 24, 0.4),
        ("The clinic record 900101-14-5678", 18, 32, 0.4),
        # fmt: on
    ],
)
def test_when_context_word_precedes_then_score_increases(
    text, expected_start, expected_end, expected_score, analyzer
):
    results = analyzer.analyze(text, language="en", entities=["MY_NRIC"])
    assert len(results) == 1
    score = pytest.approx(expected_score)
    assert_result(results[0], "MY_NRIC", expected_start, expected_end, score)


def test_accepts_name_kwarg():
    recognizer = MyNricRecognizer(name="CustomMyNric")
    assert recognizer.name == "CustomMyNric"
    assert recognizer.country_code() == "my"


def test_loads_and_detects_when_enabled_in_yaml(tmp_path, spacy_nlp_engine):
    """The recognizer loads from the shipped YAML entry once enabled."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "MyNricRecognizer"]
    assert len(entries) == 1, "MyNricRecognizer missing from YAML"
    entry = entries[0]
    assert entry["country_code"] == "my"
    assert entry["enabled"] is False

    conf_file = tmp_path / "recognizers.yaml"
    conf_file.write_text(
        yaml.safe_dump(
            {
                "supported_languages": ["en"],
                "recognizers": [dict(entry, enabled=True)],
            }
        )
    )
    registry = RecognizerRegistryProvider(
        conf_file=str(conf_file)
    ).create_recognizer_registry()
    assert [type(r).__name__ for r in registry.recognizers] == ["MyNricRecognizer"]

    analyzer = AnalyzerEngine(registry=registry, nlp_engine=spacy_nlp_engine)
    results = analyzer.analyze("Applicant 900101-14-5678 signed.", language="en")

    assert [r.entity_type for r in results] == ["MY_NRIC"]
    assert_result(results[0], "MY_NRIC", 10, 24, 0.4)
