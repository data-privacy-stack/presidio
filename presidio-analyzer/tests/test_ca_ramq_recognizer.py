from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine, EntityRecognizer, RecognizerRegistry
from presidio_analyzer.predefined_recognizers import CaRamqRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests.assertions import assert_result_within_score_range

# All numbers below are synthetic. The first four letters stand for a fictional
# surname/first name, the digits encode a fictional birth date.
STRONG = 0.65  # plausible birth date: month 01-12 or 51-62, day 01-31
BASE = 0.5  # same shape, any other digits
# Context adds the enhancer's default 0.35 boost, capped at 1.0
STRONG_WITH_CONTEXT = 1.0
WITH_CONTEXT = 0.85  # BASE + 0.35


@pytest.fixture(scope="module")
def recognizer():
    """Return the recognizer under test, default configuration."""
    return CaRamqRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the entity list requested from the recognizer."""
    return ["CA_RAMQ"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # Valid, no separator
        (
            "ABCD85031401",
            1,
            ((0, 12),),
            ((STRONG, STRONG),),
        ),
        # Valid, the printed 4-4-4 grouping
        (
            "ABCD 8503 1401",
            1,
            ((0, 14),),
            ((STRONG, STRONG),),
        ),
        # Valid, dashes between every group
        (
            "ABCD-85-03-14-01",
            1,
            ((0, 16),),
            ((STRONG, STRONG),),
        ),
        # Valid, every group separated by a space
        (
            "ABCD 85 03 14 01",
            1,
            ((0, 16),),
            ((STRONG, STRONG),),
        ),
        # Valid, mixed separators
        (
            "ABCD 8503-1401",
            1,
            ((0, 14),),
            ((STRONG, STRONG),),
        ),
        # Valid, a woman's number (50 added to the month: 53 = March)
        (
            "ABCD 8553 1401",
            1,
            ((0, 14),),
            ((STRONG, STRONG),),
        ),
        # Valid, woman's number (62 = December)
        (
            "ABCD 9962 3199",
            1,
            ((0, 14),),
            ((STRONG, STRONG),),
        ),
        # Lowercase is accepted: like the other Canadian recognizers, this one
        # relies on the base class's case-insensitive matching
        (
            "abcd 8503 1401",
            1,
            ((0, 14),),
            ((STRONG, STRONG),),
        ),
        (
            "Abcd 8503 1401",
            1,
            ((0, 14),),
            ((STRONG, STRONG),),
        ),
        # Embedded in text
        (
            "Patient ABCD 8503 1401 admitted",
            1,
            ((8, 22),),
            ((STRONG, STRONG),),
        ),
        # Followed by punctuation
        (
            "Number: ABCD 8503 1401.",
            1,
            ((8, 22),),
            ((STRONG, STRONG),),
        ),
        # Two numbers
        (
            "ABCD 8503 1401 and WXYZ 7262 0802",
            2,
            ((0, 14), (19, 33)),
            ((STRONG, STRONG), (STRONG, STRONG)),
        ),
        # The birth date ranks a match but never drops it: an impossible month
        # still matches, at the base score, and the analyzer threshold decides
        (
            "ABCD 8513 1401",
            1,
            ((0, 14),),
            ((BASE, BASE),),
        ),
        # Same for an impossible day
        (
            "ABCD 8503 3201",
            1,
            ((0, 14),),
            ((BASE, BASE),),
        ),
        # Near miss: 3 letters
        (
            "ABC 8503 1401",
            0,
            (),
            (),
        ),
        # Near miss: 5 letters
        (
            "ABCDE 8503 1401",
            0,
            (),
            (),
        ),
        # Near miss: 7 digits
        (
            "ABCD 8503 140",
            0,
            (),
            (),
        ),
        # Near miss: 9 digits
        (
            "ABCD 8503 14012",
            0,
            (),
            (),
        ),
        # Near miss: a letter among the digits
        (
            "ABCD 8503 14O1",
            0,
            (),
            (),
        ),
        # Near miss: digits before the letters
        (
            "8503 1401 ABCD",
            0,
            (),
            (),
        ),
        # Not a separator: dot, underscore, two spaces, newline
        (
            "ABCD.8503.1401",
            0,
            (),
            (),
        ),
        (
            "ABCD_85031401",
            0,
            (),
            (),
        ),
        (
            "ABCD  8503 1401",
            0,
            (),
            (),
        ),
        (
            "ABCD\n85031401",
            0,
            (),
            (),
        ),
        # Not a whole token: glued to other letters or digits
        (
            "XABCD85031401",
            0,
            (),
            (),
        ),
        (
            "ABCD850314012",
            0,
            (),
            (),
        ),
        (
            "ABCD85031401X",
            0,
            (),
            (),
        ),
        # Lookalike: invoice number, 3 letters then digits
        (
            "INV-2024-0817",
            0,
            (),
            (),
        ),
        # Lookalike: SKU with 7 digits after 4 letters
        (
            "SKU-ABCD-1234567",
            0,
            (),
            (),
        ),
        # Empty string
        (
            "",
            0,
            (),
            (),
        ),
        # fmt: on
    ],
)
def test_when_ramq_in_text_then_all_ca_ramqs_found(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
):
    """Format and separator cases, with exact boundaries."""
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len

    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )


def test_never_promotes_to_max_score(recognizer):
    """No checksum exists, so the pattern score must stand (no validation)."""
    assert recognizer.validate_result("ABCD 8503 1401") is None
    for text, score in [("ABCD 8503 1401", STRONG), ("ABCD 9999 9999", BASE)]:
        results = recognizer.analyze(text, ["CA_RAMQ"])
        assert results[0].score == pytest.approx(score)
        assert results[0].score < EntityRecognizer.MAX_SCORE


@pytest.fixture(scope="module")
def analyzer(spacy_nlp_engine):
    """Build an engine with only this recognizer, so context applies."""
    return AnalyzerEngine(
        registry=_registry_with(CaRamqRecognizer()),
        nlp_engine=spacy_nlp_engine,
        supported_languages=["en"],
        default_score_threshold=0,
    )


def _registry_with(recognizer):
    registry = RecognizerRegistry(supported_languages=["en"])
    registry.add_recognizer(recognizer)
    return registry


@pytest.mark.parametrize(
    "text, expected_score",
    [
        # fmt: off
        # No context word
        ("Patient ABCD 8503 1401 admitted", STRONG),
        # Context words before the number raise the score
        ("RAMQ number ABCD 8503 1401", STRONG_WITH_CONTEXT),
        ("The health card ABCD 8503 1401", STRONG_WITH_CONTEXT),
        ("His health insurance ABCD 8503 1401", STRONG_WITH_CONTEXT),
        ("La carte soleil ABCD 8503 1401", STRONG_WITH_CONTEXT),
        ("Numéro d'assurance maladie ABCD 8503 1401", STRONG_WITH_CONTEXT),
        # Context is prefix-only: a word after the number does not count
        ("ABCD 8503 1401 is the RAMQ number", STRONG),
        # Bare "nam" is not a context word: substring matching would let it fire
        # on "dynamic" and "naming" (measured), so the acronym is left out
        ("The dynamic ABCD 8503 1401", STRONG),
        ("Naming ABCD 8503 1401", STRONG),
        ("NAM ABCD 8503 1401", STRONG),
        # "card" alone must not count as context either
        ("Card ABCD 8503 1401", STRONG),
        # A number with an implausible date has the base score, and context
        # still adds its boost
        ("Patient ABCD 9999 9999 admitted", BASE),
        ("RAMQ number ABCD 9999 9999", WITH_CONTEXT),
        ("ABCD 9999 9999 is the RAMQ number", BASE),
        # fmt: on
    ],
)
def test_when_context_word_precedes_ramq_then_score_is_boosted(
    text, expected_score, analyzer
):
    """Context words before the number add 0.35; elsewhere they do nothing."""
    results = analyzer.analyze(text, language="en", entities=["CA_RAMQ"])
    assert len(results) == 1
    assert results[0].score == pytest.approx(expected_score)


def test_constructor_accepts_loader_kwargs_and_defaults():
    """The YAML loader passes name/supported_entity/context/supported_language."""
    default = CaRamqRecognizer()
    assert default.supported_language == "en"
    assert default.supported_entities == ["CA_RAMQ"]
    assert default.COUNTRY_CODE == "ca"

    custom = CaRamqRecognizer(
        name="CustomRamq",
        supported_entity="CUSTOM_RAMQ",
        supported_language="fr",
        context=["mon nam"],
    )
    assert custom.name == "CustomRamq"
    assert custom.supported_entities == ["CUSTOM_RAMQ"]
    assert custom.supported_language == "fr"
    assert custom.context == ["mon nam"]


def _default_entry():
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "CaRamqRecognizer"]
    assert len(entries) == 1, "CaRamqRecognizer missing from default_recognizers.yaml"
    return entries[0]


@pytest.mark.parametrize("language", ["en", "fr"])
def test_loads_from_default_recognizers_yaml(language):
    """Enabled in a registry config, the recognizer loads in en and fr.

    The top-level ``supported_languages`` is a global filter (default ``["en"]``):
    a French-only registry needs ``fr`` listed there or nothing loads.
    """
    entry = _default_entry()
    assert entry["country_code"] == "ca"
    assert entry["enabled"] is False  # country-specific: off by default
    assert language in entry["supported_languages"]

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": [language],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == ["CaRamqRecognizer"]
    assert registry.recognizers[0].supported_language == language
    assert "CA_RAMQ" in registry.recognizers[0].supported_entities


def test_recognizer_loads_and_detects_when_enabled_in_yaml(tmp_path, spacy_nlp_engine):
    """Detection must work through the path users actually configure."""
    conf = tmp_path / "recognizers.yaml"
    conf.write_text(
        """
supported_languages:
  - en
recognizers:
  - name: CaRamqRecognizer
    supported_languages:
      - en
    type: predefined
    enabled: true
    country_code: ca
"""
    )
    registry = RecognizerRegistryProvider(conf_file=conf).create_recognizer_registry()
    engine = AnalyzerEngine(
        registry=registry,
        nlp_engine=spacy_nlp_engine,
        supported_languages=["en"],
        default_score_threshold=0,
    )

    text = "RAMQ number ABCD 8503 1401, postal code unknown"
    results = engine.analyze(text, language="en")

    assert [r.entity_type for r in results] == ["CA_RAMQ"]
    assert (results[0].start, results[0].end) == (12, 26)
    assert results[0].score == pytest.approx(STRONG_WITH_CONTEXT)


@pytest.mark.parametrize(
    "text, pattern_name, plausible_date",
    [
        # Men: months 01-12
        ("ABCD 8501 1401", "CA RAMQ (strong)", True),
        ("ABCD 8512 1401", "CA RAMQ (strong)", True),
        # Women: months 51-62
        ("ABCD 8551 1401", "CA RAMQ (strong)", True),
        ("ABCD 8562 1401", "CA RAMQ (strong)", True),
        # Outside both ranges
        ("ABCD 8500 1401", "CA RAMQ (medium)", False),
        ("ABCD 8513 1401", "CA RAMQ (medium)", False),
        ("ABCD 8550 1401", "CA RAMQ (medium)", False),
        ("ABCD 8563 1401", "CA RAMQ (medium)", False),
        # Days 01-31
        ("ABCD 8503 0101", "CA RAMQ (strong)", True),
        ("ABCD 8503 3199", "CA RAMQ (strong)", True),
        ("ABCD 8503 0001", "CA RAMQ (medium)", False),
        ("ABCD 8503 3201", "CA RAMQ (medium)", False),
    ],
)
def test_birth_date_picks_one_pattern_and_never_drops_a_match(
    text, pattern_name, plausible_date, recognizer, entities
):
    """Each number matches exactly once; the date only chooses its score."""
    results = recognizer.analyze(text, entities)
    assert len(results) == 1
    assert (results[0].start, results[0].end) == (0, len(text))
    assert results[0].analysis_explanation.pattern_name == pattern_name
    assert results[0].score == pytest.approx(STRONG if plausible_date else BASE)
