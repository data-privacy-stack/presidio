"""Constructor-derived patterns must reach predefined recognizers safely."""

from unittest.mock import MagicMock

import pytest

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider


class PatternOptionRecognizer(PatternRecognizer):
    def __init__(self, patterns=None, name=None, supported_language="en"):
        super().__init__(
            name=name,
            supported_language=supported_language,
            supported_entity="PATTERN_OPTION",
            patterns=patterns or [Pattern("default", r"\bOLD\d{4}\b", 0.4)],
        )


@pytest.mark.parametrize("explicit_type", [True, False])
def test_predefined_pattern_constructor_option_is_loaded_and_detects(explicit_type):
    entry = {
        "class_name": "PatternOptionRecognizer",
        "supported_entity": "PATTERN_OPTION",
        "patterns": [{"name": "new", "regex": r"\bNEW\d{4}\b", "score": 0.65}],
    }
    if explicit_type:
        entry["type"] = "predefined"
    recognizer = (
        RecognizerRegistryProvider(registry_configuration={"recognizers": [entry]})
        .create_recognizer_registry()
        .recognizers[0]
    )
    assert type(recognizer) is (
        PatternOptionRecognizer if explicit_type else PatternRecognizer
    )
    assert [
        (r.start, r.end, r.score)
        for r in recognizer.analyze("Record NEW1234.", ["PATTERN_OPTION"])
    ] == [(7, 14, 0.65)]
    assert recognizer.analyze("Record OLD1234 or NEW123X.", ["PATTERN_OPTION"]) == []


@pytest.mark.parametrize(
    "pattern,fragment",
    [
        (
            {"name": "invalid", "regex": "[", "score": 0.5},
            "invalid patterns[0] regex syntax at position 1",
        ),
        ({"name": "invalid", "regex": "x"}, "Pattern should contain a score field"),
        (
            {"name": "invalid", "regex": "x", "score": 1.1},
            "Pattern score should be between 0 and 1",
        ),
        (
            {"name": "invalid", "regex": 123, "score": 0.5},
            "Pattern regex should be a string",
        ),
    ],
)
@pytest.mark.parametrize("custom", [True, False])
def test_invalid_patterns_fail_before_any_recognizer_load(
    pattern, fragment, custom, monkeypatch
):
    entry = (
        {"name": "custom", "supported_entity": "PATTERN_OPTION"}
        if custom
        else {"class_name": "PatternOptionRecognizer", "type": "predefined"}
    )
    entry["patterns"] = [pattern]
    load = MagicMock()
    monkeypatch.setattr(PatternRecognizer, "load", load)
    with pytest.raises(ValueError) as exc:
        RecognizerRegistryProvider(
            registry_configuration={"recognizers": [entry]}
        ).create_recognizer_registry()
    assert fragment in str(exc.value) + str(exc.value.__cause__)
    load.assert_not_called()


def test_invalid_later_pattern_prevents_loading_earlier_recognizers(monkeypatch):
    load = MagicMock()
    monkeypatch.setattr(PatternRecognizer, "load", load)
    with pytest.raises(ValueError, match="regex"):
        RecognizerRegistryProvider(
            registry_configuration={
                "recognizers": [
                    {"class_name": "PatternOptionRecognizer"},
                    {
                        "name": "invalid",
                        "supported_entity": "TEST",
                        "patterns": [{"name": "invalid", "regex": "[", "score": 0.5}],
                    },
                ],
            }
        ).create_recognizer_registry()
    load.assert_not_called()


def test_non_pattern_recognizer_constructor_field_remains_opaque():
    class OpaquePatternsRecognizer(EntityRecognizer):
        def __init__(self, patterns, name=None, supported_language="en"):
            self.patterns = patterns
            super().__init__(
                ["OPAQUE"], name=name, supported_language=supported_language
            )

        def load(self):
            pass

        def analyze(self, text, entities, nlp_artifacts=None):
            return []

    recognizer = (
        RecognizerRegistryProvider(
            registry_configuration={
                "recognizers": [
                    {
                        "class_name": "OpaquePatternsRecognizer",
                        "type": "predefined",
                        "patterns": {"not": "a regex configuration"},
                    }
                ]
            }
        )
        .create_recognizer_registry()
        .recognizers[0]
    )
    assert recognizer.patterns == {"not": "a regex configuration"}
