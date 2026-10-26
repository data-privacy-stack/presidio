"""Predefined pattern recognizers with normalize_text enabled.

Covers review comments 2 and 3 on the normalization PR: predefined
recognizers accept the flag in their constructors (including IBAN, whose
own analyze previously skipped the second pass), and the analyzer engine
builds the normalized view once per text.
"""

import pytest
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, RecognizerRegistry
from presidio_analyzer.nlp_engine import NoOpNlpEngine
from presidio_analyzer.predefined_recognizers.country_specific.us.us_ssn_recognizer import (  # noqa: E501
    UsSsnRecognizer,
)
from presidio_analyzer.predefined_recognizers.generic.credit_card_recognizer import (
    CreditCardRecognizer,
)
from presidio_analyzer.predefined_recognizers.generic.crypto_recognizer import (
    CryptoRecognizer,
)
from presidio_analyzer.predefined_recognizers.generic.date_recognizer import (
    DateRecognizer,
)
from presidio_analyzer.predefined_recognizers.generic.email_recognizer import (
    EmailRecognizer,
)
from presidio_analyzer.predefined_recognizers.generic.iban_recognizer import (
    IbanRecognizer,
)
from presidio_analyzer.predefined_recognizers.generic.ip_recognizer import (
    IpRecognizer,
)
from presidio_analyzer.predefined_recognizers.generic.mac_recognizer import (
    MacAddressRecognizer,
)
from presidio_analyzer.predefined_recognizers.generic.url_recognizer import (
    UrlRecognizer,
)
from presidio_analyzer.predefined_recognizers.generic.uuid_recognizer import (
    UuidRecognizer,
)
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider
from presidio_analyzer.text_normalization import needs_normalized_view


def to_fullwidth(text: str) -> str:
    """Map ASCII printable characters to their full-width forms."""
    return "".join(
        chr(ord(char) + 0xFEE0) if 0x21 <= ord(char) <= 0x7E else char for char in text
    )


# (recognizer class, valid ASCII sample, entity, expected score)
# Samples are values the recognizer accepts on raw text too, so the only
# variable under test is the full-width form.
PREDEFINED_CASES = [
    (CreditCardRecognizer, "4111111111111111", "CREDIT_CARD", 1.0),
    (CryptoRecognizer, "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "CRYPTO", 1.0),
    (DateRecognizer, "01/02/2024", "DATE_TIME", 0.6),
    (EmailRecognizer, "test@example.com", "EMAIL_ADDRESS", 1.0),
    (IbanRecognizer, "DE89370400440532013000", "IBAN_CODE", 1.0),
    (IpRecognizer, "192.168.0.1", "IP_ADDRESS", 0.6),
    (MacAddressRecognizer, "AA:BB:CC:DD:EE:FF", "MAC_ADDRESS", 0.6),
    (UrlRecognizer, "https://example.com", "URL", 0.6),
    (UuidRecognizer, "123e4567-e89b-12d3-a456-426614174000", "UUID", 0.5),
    (UsSsnRecognizer, "234-56-7890", "US_SSN", 0.5),
]


@pytest.mark.parametrize(
    "recognizer_cls, sample, entity, expected_score", PREDEFINED_CASES
)
def test_predefined_recognizer_detects_fullwidth_sample(
    recognizer_cls, sample, entity, expected_score
):
    """Constructor flag on: full-width sample detected with original spans."""
    recognizer = recognizer_cls(normalize_text=True)
    assert recognizer.normalize_text is True

    results = recognizer.analyze(to_fullwidth(sample), [entity])

    assert [(r.entity_type, r.start, r.end) for r in results] == [
        (entity, 0, len(sample))
    ]
    assert results[0].score == pytest.approx(expected_score)


@pytest.mark.parametrize(
    "recognizer_cls, sample, entity, expected_score", PREDEFINED_CASES
)
def test_predefined_recognizer_flag_off_misses_fullwidth_sample(
    recognizer_cls, sample, entity, expected_score
):
    """Flag off (the default): the same full-width sample is missed."""
    recognizer = recognizer_cls()

    assert recognizer.analyze(to_fullwidth(sample), [entity]) == []


@pytest.mark.parametrize(
    "recognizer_cls, sample, entity, expected_score", PREDEFINED_CASES
)
def test_predefined_recognizer_loads_with_flag_from_yaml(
    tmp_path, recognizer_cls, sample, entity, expected_score
):
    """YAML predefined entry with normalize_text reaches the recognizer."""
    conf = tmp_path / "recognizers.yaml"
    country_code = "\n    country_code: us" if recognizer_cls is UsSsnRecognizer else ""
    conf.write_text(
        f"""
supported_languages:
  - en
recognizers:
  - name: {recognizer_cls.__name__}
    supported_languages:
      - en
    type: predefined
    enabled: true{country_code}
    normalize_text: true
"""
    )
    registry = RecognizerRegistryProvider(conf_file=conf).create_recognizer_registry()

    (recognizer,) = [r for r in registry.recognizers if isinstance(r, recognizer_cls)]

    assert recognizer.normalize_text is True
    results = recognizer.analyze(to_fullwidth(sample), [entity])
    assert [(r.entity_type, r.start, r.end) for r in results] == [
        (entity, 0, len(sample))
    ]


def test_iban_detects_fullwidth_with_surrounding_text():
    """IBAN spans map back to original offsets, not normalized offsets."""
    recognizer = IbanRecognizer(normalize_text=True)
    text = "pay " + to_fullwidth("DE89370400440532013000") + " now"

    results = recognizer.analyze(text, ["IBAN_CODE"])

    assert [(r.entity_type, r.start, r.end) for r in results] == [("IBAN_CODE", 4, 26)]


def test_iban_detects_zero_width_separated_iban():
    """IBAN split by zero-width spaces is detected across the full span."""
    recognizer = IbanRecognizer(normalize_text=True)
    zwsp = chr(0x200B)
    text = "DE89" + zwsp + "370400440532013000"

    results = recognizer.analyze(text, ["IBAN_CODE"])

    assert [(r.entity_type, r.start, r.end) for r in results] == [
        ("IBAN_CODE", 0, len(text))
    ]


def test_needs_normalized_view():
    """Fast-path helper: clean text needs no view, variants do."""
    assert needs_normalized_view("hello world") is False
    assert needs_normalized_view(to_fullwidth("123")) is True
    assert needs_normalized_view("a" + chr(0x200B) + "b") is True


def test_pattern_recognizer_skips_view_build_for_clean_text(monkeypatch):
    """Already-normalized text never pays for a view build."""
    import presidio_analyzer.pattern_recognizer as pattern_recognizer_module

    calls = []
    real_build = pattern_recognizer_module.build_normalized_view

    def counting_build(text):
        calls.append(text)
        return real_build(text)

    monkeypatch.setattr(
        pattern_recognizer_module, "build_normalized_view", counting_build
    )
    recognizer = EmailRecognizer(normalize_text=True)

    recognizer.analyze("test@example.com", ["EMAIL_ADDRESS"])

    assert calls == []


def test_engine_builds_normalized_view_once_per_text(monkeypatch):
    """Two flag-on recognizers share one engine-built view."""
    import presidio_analyzer.analyzer_engine as analyzer_engine_module

    calls = []
    real_build = analyzer_engine_module.build_normalized_view

    def counting_build(text):
        calls.append(text)
        return real_build(text)

    monkeypatch.setattr(analyzer_engine_module, "build_normalized_view", counting_build)
    registry = RecognizerRegistry(
        recognizers=[
            CreditCardRecognizer(normalize_text=True),
            EmailRecognizer(normalize_text=True),
        ],
        supported_languages=["en"],
    )
    analyzer = AnalyzerEngine(
        registry=registry,
        nlp_engine=NoOpNlpEngine(models=[{"lang_code": "en", "model_name": "no_op"}]),
    )
    text = (
        "card "
        + to_fullwidth("4111111111111111")
        + " mail "
        + to_fullwidth("test@example.com")
    )

    results = analyzer.analyze(text, language="en")

    assert {r.entity_type for r in results} == {"CREDIT_CARD", "EMAIL_ADDRESS"}
    assert len(calls) == 1


def test_engine_builds_no_view_when_flag_off(monkeypatch):
    """Flag off everywhere: the engine never builds a view."""
    import presidio_analyzer.analyzer_engine as analyzer_engine_module

    calls = []
    real_build = analyzer_engine_module.build_normalized_view

    def counting_build(text):
        calls.append(text)
        return real_build(text)

    monkeypatch.setattr(analyzer_engine_module, "build_normalized_view", counting_build)
    registry = RecognizerRegistry(
        recognizers=[CreditCardRecognizer(), EmailRecognizer()],
        supported_languages=["en"],
    )
    analyzer = AnalyzerEngine(
        registry=registry,
        nlp_engine=NoOpNlpEngine(models=[{"lang_code": "en", "model_name": "no_op"}]),
    )

    analyzer.analyze("card 4111111111111111", language="en")

    assert calls == []


@pytest.mark.parametrize("email_normalize_text", [True, False])
def test_engine_keeps_custom_analyze_override_working(email_normalize_text):
    """Old-signature analyze overrides still work through the engine."""

    class LegacyAnalyzeRecognizer(PatternRecognizer):
        def analyze(self, text, entities, nlp_artifacts=None, regex_flags=None):
            return super().analyze(text, entities, nlp_artifacts, regex_flags)

    registry = RecognizerRegistry(
        recognizers=[
            LegacyAnalyzeRecognizer(supported_entity="TITLE", deny_list=["Mr."]),
            EmailRecognizer(normalize_text=email_normalize_text),
        ],
        supported_languages=["en"],
    )
    analyzer = AnalyzerEngine(
        registry=registry,
        nlp_engine=NoOpNlpEngine(models=[{"lang_code": "en", "model_name": "no_op"}]),
    )

    results = analyzer.analyze(
        "Mr. Smith, " + to_fullwidth("test@example.com"), language="en"
    )

    expected = {"TITLE", "EMAIL_ADDRESS"} if email_normalize_text else {"TITLE"}
    assert {r.entity_type for r in results} == expected
