"""Recognizer names, model identities, and pre-load duplicate diagnostics."""

from unittest.mock import MagicMock

import pytest

from presidio_analyzer import PatternRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider


class IdentityModelRecognizer(PatternRecognizer):
    def __init__(
        self, model_name="example/default", name=None, supported_language="en"
    ):
        self.model_name = model_name
        super().__init__(
            name=name,
            supported_language=supported_language,
            supported_entity="IDENTITY_REFERENCE",
            deny_list=["REF1234"],
        )


def registry(*entries, languages=None):
    return RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": languages if languages is not None else ["en"],
            "recognizers": list(entries),
        }
    ).create_recognizer_registry()


@pytest.mark.parametrize(
    "entry,expected",
    [
        ({"class_name": "CreditCardRecognizer"}, "CreditCardRecognizer"),
        (
            {"class_name": "IdentityModelRecognizer"},
            "IdentityModelRecognizer:example/default",
        ),
        (
            {"class_name": "IdentityModelRecognizer", "model_name": "example/other"},
            "IdentityModelRecognizer:example/other",
        ),
        (
            {"class_name": "IdentityModelRecognizer", "name": "my-model"},
            "my-model",
        ),
        ({"name": "IdentityModelRecognizer"}, "IdentityModelRecognizer"),
        ("IdentityModelRecognizer", "IdentityModelRecognizer"),
    ],
)
def test_name_derivation_preserves_explicit_and_legacy_names(entry, expected):
    assert registry(entry).recognizers[0].name == expected


def test_different_models_get_distinct_readable_names_and_detect():
    result = registry(
        {"class_name": "IdentityModelRecognizer", "model_name": "example/one"},
        {"class_name": "IdentityModelRecognizer", "model_name": "example/two"},
    )
    assert [r.name for r in result.recognizers] == [
        "IdentityModelRecognizer:example/one",
        "IdentityModelRecognizer:example/two",
    ]
    for recognizer in result.recognizers:
        assert [
            (r.start, r.end, r.score)
            for r in recognizer.analyze("Record REF1234.", ["IDENTITY_REFERENCE"])
        ] == [(7, 14, 1.0)]
        assert recognizer.analyze("Record REF123X.", ["IDENTITY_REFERENCE"]) == []


@pytest.mark.parametrize(
    "entries,fragment",
    [
        (
            [{"name": "IdentityModelRecognizer"}] * 2,
            "Duplicate recognizer",
        ),
        (
            ["IdentityModelRecognizer", {"name": "IdentityModelRecognizer"}],
            "Duplicate recognizer",
        ),
        (
            [
                {"class_name": "IdentityModelRecognizer"},
                {"class_name": "IdentityModelRecognizer", "name": "explicit"},
            ],
            "explicit unique names",
        ),
        (
            [
                {
                    "class_name": "IdentityModelRecognizer",
                    "model_name": "example/default",
                },
                {"class_name": "IdentityModelRecognizer", "name": "explicit"},
            ],
            "explicit unique names",
        ),
        (
            [{"name": "IdentityModelRecognizer", "supported_languages": ["en", "en"]}],
            "Duplicate recognizer",
        ),
    ],
)
def test_ambiguous_identity_is_rejected_before_any_model_load(
    entries, fragment, monkeypatch
):
    load = MagicMock()
    monkeypatch.setattr(IdentityModelRecognizer, "load", load)
    with pytest.raises(ValueError) as exc:
        registry(*entries)
    assert fragment in str(exc.value) + str(exc.value.__cause__)
    load.assert_not_called()


def test_repeated_models_with_explicit_unique_names_are_supported():
    result = registry(
        {"class_name": "IdentityModelRecognizer", "name": "first"},
        {"class_name": "IdentityModelRecognizer", "name": "second"},
    )
    assert [r.name for r in result.recognizers] == ["first", "second"]


def test_same_identity_in_distinct_languages_is_supported():
    result = registry(
        {"name": "IdentityModelRecognizer", "supported_language": "en"},
        {"name": "IdentityModelRecognizer", "supported_language": "es"},
        languages=["en", "es"],
    )
    assert [(r.name, r.supported_language) for r in result.recognizers] == [
        ("IdentityModelRecognizer", "en"),
        ("IdentityModelRecognizer", "es"),
    ]


def test_disabled_or_globally_excluded_entries_do_not_collide():
    result = registry(
        {"class_name": "IdentityModelRecognizer"},
        {"class_name": "IdentityModelRecognizer", "enabled": False},
        {"class_name": "IdentityModelRecognizer", "supported_language": "es"},
    )
    assert [(r.name, r.supported_language) for r in result.recognizers] == [
        ("IdentityModelRecognizer:example/default", "en")
    ]


def test_explicit_empty_language_list_constructs_nothing():
    assert (
        registry(
            {"name": "IdentityModelRecognizer", "supported_languages": []}
        ).recognizers
        == []
    )


@pytest.mark.parametrize("name", ["", " "])
def test_empty_names_are_rejected_instead_of_silently_defaulting(name):
    with pytest.raises(ValueError) as exc:
        registry({"class_name": "IdentityModelRecognizer", "name": name})
    assert "name must be a non-empty string" in str(exc.value.__cause__)


def test_custom_and_predefined_names_share_the_same_identity_namespace():
    with pytest.raises(ValueError) as exc:
        registry(
            {"class_name": "IdentityModelRecognizer", "name": "shared"},
            {
                "name": "shared",
                "supported_entity": "CUSTOM",
                "deny_list": ["REF1234"],
            },
        )
    assert "Duplicate recognizer" in str(exc.value.__cause__)


def test_unknown_bare_class_is_rejected_before_model_loading():
    with pytest.raises(ValueError) as exc:
        registry("UnknownIdentityRecognizer")
    assert "not found" in str(exc.value.__cause__)


def test_predefined_singular_language_outside_registry_is_filtered():
    assert registry(
        {"name": "IdentityModelRecognizer", "supported_language": "es"}
    ).recognizers == []


def test_duplicate_global_language_error_names_the_language_setting():
    with pytest.raises(ValueError) as exc:
        registry({"name": "IdentityModelRecognizer"}, languages=["en", "en"])
    assert "remove repeated language codes" in str(exc.value.__cause__)
