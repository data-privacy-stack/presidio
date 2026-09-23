"""Conformance suite for the recognizer registry / YAML configuration layer.

Presidio's YAML configuration layer is a public contract: a key a user can
set in a registry YAML file either reaches the object it configures, or the
registry raises a message naming the key. This module is the regression
suite that turns that promise into something CI checks, rather than
something a user discovers when they flip ``enabled: true``:

- Story 1/2: every concrete recognizer's constructor must accept the keys
  ``RecognizerListLoader`` injects unconditionally (``name`` and
  ``supported_language``) plus one of ``supported_entity``/
  ``supported_entities``, or enabling it in YAML crashes registry
  construction with a distant ``TypeError`` instead of a clear failure here.
  ``context`` is deliberately not part of the contract: it is one flat word
  list applied to every result, so multi-entity recognizers do not accept
  it, and the loader drops it with a warning for them instead.
- Story 3: every entry in the shipped ``conf/default_recognizers.yaml``
  loads, and every field it sets reaches the constructed recognizer.
- Story 4: a synthetic YAML entry for *every* concrete recognizer class
  round-trips its ``name``, ``context``, and ``score_thresholds`` -- and an
  unknown key is never silently dropped.
"""

from __future__ import annotations

import importlib.util
import inspect
from typing import Any, Dict, List, Set, Tuple, Type

import presidio_analyzer.predefined_recognizers  # noqa: F401 -- see below
import pytest
from presidio_analyzer import EntityRecognizer, PatternRecognizer
from presidio_analyzer.input_validation.recognizer_configuration import (
    derive_config_model,
)
from presidio_analyzer.input_validation.yaml_recognizer_models import (
    BaseRecognizerConfig,
    CustomRecognizerConfig,
    PredefinedRecognizerConfig,
)
from presidio_analyzer.predefined_recognizers import CreditCardRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider
from presidio_analyzer.recognizer_registry.recognizers_loader_utils import (
    RecognizerListLoader,
)
from presidio_analyzer.score_thresholds import normalize_score_thresholds
from pydantic_core import PydanticUndefined

from tests.test_recognizers_loader_utils import (
    DEFAULT_CONF_DATA,
    GLOBAL_REGEX_FLAGS,
    NOT_LOADABLE_FROM_SHIPPED_ENTRY,
    PACKAGE_ROOT,
)

# The import above registers every concrete predefined-recognizer subclass on
# ``EntityRecognizer`` before ``get_all_existing_recognizers()`` is called
# below -- it is otherwise unused in this module.

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------


def _is_test_double(cls: type) -> bool:
    """Return True for a recognizer subclass defined inside the test suite.

    Several test modules define a throwaway ``PatternRecognizer`` subclass at
    module scope for their own tests. Those are not part of the product's
    recognizer contract and must not be swept into this conformance suite.
    """
    module = getattr(cls, "__module__", "") or ""
    return module == "tests" or module.startswith("tests.")


def _concrete_recognizer_classes() -> List[Type[EntityRecognizer]]:
    return sorted(
        (
            cls
            for cls in RecognizerListLoader.get_all_existing_recognizers()
            if not inspect.isabstract(cls) and not _is_test_double(cls)
        ),
        key=lambda cls: cls.__name__,
    )


# Every concrete (non-abstract, non-test-double) ``EntityRecognizer``
# subclass presidio ships. Computed once at import time and reused by every
# story below so they all agree on exactly what "every recognizer" means.
CONCRETE_RECOGNIZER_CLASSES = _concrete_recognizer_classes()
CONCRETE_RECOGNIZER_CLASSES_BY_NAME: Dict[str, Type[EntityRecognizer]] = {
    cls.__name__: cls for cls in CONCRETE_RECOGNIZER_CLASSES
}


@pytest.fixture
def patched_loads(monkeypatch):
    """Patch ``load`` to a no-op on every concrete recognizer class.

    Constructing a recognizer from configuration can otherwise attempt to
    download a real model (HuggingFace, GLiNER, spaCy...) -- forbidden in a
    test. This suite only proves that configuration keys reach the
    constructed object, never that a model actually loads, so no test here
    may exercise a real ``load()``.
    """
    for cls in CONCRETE_RECOGNIZER_CLASSES:
        monkeypatch.setattr(cls, "load", lambda self: None, raising=False)


# A recognizer whose constructor imports an optional extra declares the
# modules it needs on the class itself, via
# ``EntityRecognizer.OPTIONAL_DEPENDENCY_MODULES`` (see its docstring) --
# colocated with the code that needs it rather than a list maintained here,
# so a subclass with the same requirement (e.g. ``MedicalNERRecognizer``
# inheriting from ``HuggingFaceNerRecognizer``) picks it up automatically,
# and a newly added optional-dependency recognizer is covered the moment its
# author follows the same one-line pattern as its siblings.
#
# On the supported core/dev install (no ``--all-extras``) these constructors
# refuse to build with an actionable ImportError/ValueError -- intended
# behavior, not a conformance failure -- so the parametrized cases below
# report a skip instead of a hard failure. The skip is decided by probing
# for the module, not by catching the exception: an unexpected ImportError
# from any class still fails the test rather than turning green. A class
# whose optional import happens only in ``load()`` (GLiNER, Stanza,
# Transformers NER) declares nothing here -- this suite patches ``load`` to
# a no-op, so it constructs without the extra.
def _skip_if_optional_dependency_missing(cls: Type[EntityRecognizer]) -> None:
    """Skip when the class needs an optional extra that is not installed."""
    for module in cls.OPTIONAL_DEPENDENCY_MODULES:
        try:
            found = importlib.util.find_spec(module) is not None
        except (ImportError, ValueError):
            found = False
        if not found:
            pytest.skip(
                f"{cls.__name__} needs optional dependency {module!r}; install "
                f"the extras (uv sync --all-extras) to run this conformance "
                f"case"
            )


# ---------------------------------------------------------------------------
# Story 1 & 2: base-class contract conformance
# ---------------------------------------------------------------------------

# Keys ``RecognizerListLoader`` injects into every predefined recognizer it
# builds from a registry entry (see ``RecognizerListLoader.get`` /
# ``_prepare_recognizer_kwargs``). ``context`` is also injected when the
# entry sets it, but it is not a contract requirement: context words only
# boost a result's score when they match text near the recognized entity,
# which only makes sense for single-entity recognizers, so multi-entity
# recognizers (NER models, remote PHI services,
# LLM extractors) do not accept it and ``_prepare_recognizer_kwargs`` drops
# it for them with a warning. See ``test_context_dropped_with_warning...``
# in ``test_recognizers_loader_utils.py`` and the round-trip test below.
REGISTRY_INJECTED_KEYS = ("name", "supported_language")
ENTITY_KEYS = ("supported_entity", "supported_entities")

# These LangExtract-based recognizers take their supported entities from the
# YAML file at ``config_path`` (see ``LangExtractRecognizer.__init__`` /
# ``get_supported_entities``), never from a ``supported_entity(ies)``
# constructor kwarg, so the entity-key requirement below does not apply to
# them. ``LangExtractRecognizer`` itself is abstract and never reaches the
# parametrized test below, but is listed for completeness/documentation.
ENTITIES_FROM_OWN_CONFIG = {
    "LangExtractRecognizer",
    "BasicLangExtractRecognizer",
    "AzureOpenAILangExtractRecognizer",
}

# Regression lock: classes whose constructor cannot yet accept every key the
# registry loader injects, mapped to exactly which keys are missing.
# Verified against the real signatures via
# ``RecognizerListLoader._reachable_init_param_names`` -- the test asserts
# the *actual* gap set equals this dict exactly,
# so fixing a class without shrinking this dict fails the test, and so does
# a newly introduced regression.
#
# Empty at the time this suite was added: every concrete recognizer accepts
# ``name``, ``supported_language`` and an entity key (or is exempt via
# ``ENTITIES_FROM_OWN_CONFIG``).
KNOWN_CONTRACT_GAPS: Dict[str, Set[str]] = {}


def _missing_registry_keys(cls: Type[EntityRecognizer]) -> Set[str]:
    reachable = RecognizerListLoader._reachable_init_param_names(cls)
    missing = {key for key in REGISTRY_INJECTED_KEYS if key not in reachable}
    if cls.__name__ not in ENTITIES_FROM_OWN_CONFIG and not any(
        key in reachable for key in ENTITY_KEYS
    ):
        missing.add("supported_entity/supported_entities")
    return missing


@pytest.mark.parametrize(
    "cls", CONCRETE_RECOGNIZER_CLASSES, ids=lambda cls: cls.__name__
)
def test_recognizer_accepts_registry_injected_keys(cls):
    """Assert the constructor accepts every key the registry loader injects.

    A constructor that rejects one of these crashes registry construction
    the moment a user enables that recognizer in YAML --
    ``TypeError: __init__() got an unexpected keyword argument ...`` -- for
    the *whole* registry, not just this recognizer. Catch that here instead.
    """
    missing = _missing_registry_keys(cls)
    expected = KNOWN_CONTRACT_GAPS.get(cls.__name__, set())
    assert missing == expected, (
        f"{cls.__name__} is missing registry-injected keys {sorted(missing)}; "
        f"KNOWN_CONTRACT_GAPS expects exactly {sorted(expected)}. Either make "
        f"the constructor accept the missing key(s), or update "
        f"KNOWN_CONTRACT_GAPS to match reality."
    )


# ---------------------------------------------------------------------------
# Story 3: shipped configuration field-reach test
# ---------------------------------------------------------------------------


def _shipped_entries() -> List[Dict[str, Any]]:
    """Normalize every entry of the shipped ``default_recognizers.yaml``.

    Mirrors ``RecognizerListLoader._split_recognizers``, which expands the
    bare-string shorthand into the same dict before building anything. The
    shorthand's own load path is covered directly in
    ``tests/test_recognizers_loader_utils.py`` (``test_bare_string_*``), so the
    parametrization here only needs each entry in its mapping form.
    """
    entries = []
    for entry in DEFAULT_CONF_DATA["recognizers"]:
        entries.append(
            {"name": entry, "type": "predefined"}
            if isinstance(entry, str)
            else dict(entry)
        )
    return entries


def _entry_id(entry: Dict[str, Any]) -> str:
    return entry.get("class_name") or entry["name"]


def _entry_language_configs(entry: Dict[str, Any]) -> List[Tuple[str, Any]]:
    """(language, context) pairs, in the shape the loader builds per language.

    Mirrors ``RecognizerListLoader._get_recognizer_languages``: a missing
    ``supported_languages`` falls back to the file's top-level languages, a
    bare list of language codes carries no per-language context, and a list
    of ``{language, context}`` dicts carries whatever context each one sets
    (``None`` if it sets none).
    """
    languages = entry.get("supported_languages")
    if languages is None:
        # The loader carries the entry-level ``context`` into every fallback
        # language (``_get_recognizer_context``), so the expectation must too;
        # returning None here would stop checking context for these entries.
        entry_context = entry.get("context")
        return [
            (language, entry_context)
            for language in DEFAULT_CONF_DATA.get("supported_languages") or ["en"]
        ]
    if not languages:
        raise AssertionError(
            f"{_entry_id(entry)}: supported_languages is an empty list; the "
            f"loader indexes element 0 and would raise IndexError"
        )
    if isinstance(languages[0], str):
        return [(language, entry.get("context")) for language in languages]
    return [(item["language"], item.get("context")) for item in languages]


SHIPPED_ENTRIES = _shipped_entries()
# Entries that cannot construct from their shipped configuration alone (see
# the set's own docstring/comment in tests/test_recognizers_loader_utils.py
# for why) -- reused here rather than duplicated, so exactly one such set
# exists in the test suite.
LOADABLE_SHIPPED_ENTRIES = [
    entry
    for entry in SHIPPED_ENTRIES
    if _entry_id(entry) not in NOT_LOADABLE_FROM_SHIPPED_ENTRY
]


@pytest.mark.parametrize("entry", LOADABLE_SHIPPED_ENTRIES, ids=_entry_id)
def test_shipped_entry_fields_reach_constructed_recognizer(
    entry, patched_loads, monkeypatch
):
    """Every shipped entry loads, and every field it sets reaches the object.

    Builds a single-recognizer registry config from one shipped entry (with
    ``enabled`` forced true) and loads it through
    ``RecognizerRegistryProvider`` -- the same path a real user's YAML goes
    through -- then checks that the entry's language(s), per-language
    context, name, and (when set) ``supported_entities`` /
    ``score_thresholds`` all reached the constructed instance(s).

    Runs from ``PACKAGE_ROOT`` so a ``config_path`` the recognizer resolves
    against the working directory behaves as it does in CI (mirroring
    ``test_yaml_entry_loads_when_enabled`` in
    ``test_recognizers_loader_utils.py``).
    """
    entry_id = _entry_id(entry)
    entry_cls = CONCRETE_RECOGNIZER_CLASSES_BY_NAME.get(entry_id)
    if entry_cls is not None:
        _skip_if_optional_dependency_missing(entry_cls)
    language_configs = _entry_language_configs(entry)
    languages = [language for language, _ in language_configs]
    conf_entry = dict(entry, enabled=True)
    configuration = {
        "global_regex_flags": GLOBAL_REGEX_FLAGS,
        "supported_languages": languages,
        "recognizers": [conf_entry],
    }
    monkeypatch.chdir(PACKAGE_ROOT)

    registry = RecognizerRegistryProvider(
        registry_configuration=configuration
    ).create_recognizer_registry()

    instances = [r for r in registry.recognizers if type(r).__name__ == entry_id]
    assert len(instances) == len(languages), (
        f"{entry_id}: expected one instance per language {languages}, got "
        f"{[r.supported_language for r in instances]}"
    )

    by_language = {instance.supported_language: instance for instance in instances}
    assert set(by_language) == set(languages), (
        f"{entry_id}: constructed languages {sorted(by_language)} do not match "
        f"the entry's languages {sorted(languages)}"
    )

    for language, context in language_configs:
        if context is not None:
            assert by_language[language].context == context, (
                f"{entry_id}/{language}: context {context!r} from the shipped "
                f"entry did not reach the constructed recognizer"
            )

    for instance in instances:
        assert instance.name == entry["name"], (
            f"{entry_id}: entry name {entry['name']!r} did not reach the "
            f"constructed recognizer"
        )

    if entry.get("supported_entities") is not None:
        # Key presence, not truthiness: an entry that explicitly sets
        # ``supported_entities: []`` is a configured value like any other and
        # must still be asserted, not treated as "not set".
        for instance in instances:
            assert instance.supported_entities == entry["supported_entities"], (
                f"{entry_id}: supported_entities "
                f"{entry['supported_entities']!r} from the shipped entry did "
                f"not reach the constructed recognizer"
            )

    if entry.get("score_thresholds") is not None:
        expected_thresholds = normalize_score_thresholds(entry["score_thresholds"])
        for instance in instances:
            assert instance.score_thresholds == expected_thresholds


# ---------------------------------------------------------------------------
# Story 4: per-class round-trip and no-silent-drop tests
# ---------------------------------------------------------------------------

# Constructor kwargs a class needs beyond what the synthetic entry below
# already supplies, keyed by class name. Most concrete recognizers construct
# fine from the synthetic entry's fields alone (constructor defaults handle
# the rest); these are the exceptions that need a value with no usable
# default.
REQUIRED_KWARGS: Dict[str, Dict[str, Any]] = {
    "LocalRecognizer": {"supported_entities": ["TEST"]},
    # No default endpoint; the constructor raises ValueError without one.
    "AzureOpenAILangExtractRecognizer": {
        "azure_endpoint": "https://example-resource.openai.azure.com/"
    },
    # HuggingFaceNerRecognizer.load() requires model_name. load() is patched
    # to a no-op for this test (see `patched_loads`), so this is not
    # strictly required for construction to succeed -- supplied anyway for a
    # realistic entry, per this dict's own purpose.
    "HuggingFaceNerRecognizer": {"model_name": "dslim/bert-base-NER"},
}

# Environment variables a class's constructor reads directly (not via a
# registry YAML kwarg) and needs set to construct without real credentials.
REQUIRED_ENV: Dict[str, Dict[str, str]] = {
    # AzureHealthDeidRecognizer needs either a `client` instance or these two
    # env vars to build its default Azure client. `client` cannot be
    # supplied through a registry entry -- the schema
    # (`PredefinedRecognizerConfig`) has no `client` field and silently
    # drops unknown keys -- so the env-var path is the only one reachable
    # from configuration, and the only one this test can exercise.
    "AzureHealthDeidRecognizer": {
        "AHDS_ENDPOINT": "https://fake.endpoint.example",
        "ENV": "development",
    },
    # Same shape as AzureHealthDeidRecognizer above: azure_ai_key /
    # azure_ai_endpoint are real constructor parameters, but
    # AzureAILanguageRecognizer also has no dedicated entry in
    # CONFIG_MODEL_MAP, so PredefinedRecognizerConfig's default
    # extra="ignore" drops them if passed as registry kwargs. The
    # constructor's own env-var fallback is the only reachable path.
    "AzureAILanguageRecognizer": {
        "AZURE_AI_KEY": "fake-key",
        "AZURE_AI_ENDPOINT": "https://fake.endpoint.example",
    },
}

# Classes whose constructor accepts `context` but do not apply it to the
# constructed instance. Pre-existing behavior this turn does not change --
# see BasicLangExtractRecognizer's own docstring ("context ... optional,
# currently not used by LLM recognizers"). The round-trip test below skips
# only the context assertion for these classes. Classes that do not accept
# `context` at all are handled dynamically: the loader drops the key with a
# warning and the instance keeps the base-class default, ``[]``.
CONTEXT_NOT_APPLIED = {"BasicLangExtractRecognizer"}

# Classes that cannot be constructed through a `type: predefined` registry
# entry at all, even with REQUIRED_KWARGS -- not a config-layer gap, but a
# structural mismatch this suite cannot paper over:
NOT_LOADABLE_AS_PREDEFINED_ENTRY = {
    # Requires `supported_entity` and (`patterns` or `deny_list`)
    # positionally. The last two can only be set through a registry entry
    # with `type: custom` -- `RecognizerRegistryConfig.parse_recognizers`
    # rejects `patterns`/`deny_list` on a `type: predefined` entry outright
    # ("... is marked as 'predefined' but contains 'patterns' or
    # 'deny_list' ..."), so no predefined entry can ever supply them.
    "PatternRecognizer",
    # Requires `target_classification` positionally, with no default and no
    # schema field to set it from (base `PredefinedRecognizerConfig` has
    # none, and no CONFIG_MODEL_MAP entry adds one) -- a base class for
    # subclassing (ZaMobileNumberRecognizer, ZaTelephoneNumberRecognizer),
    # never meant to be named directly in configuration.
    "ZaPhoneNumberRecognizer",
}


def _synthetic_entry(cls: Type[EntityRecognizer]) -> Dict[str, Any]:
    return {
        "name": f"conf_{cls.__name__}",
        "class_name": cls.__name__,
        "type": "predefined",
        "supported_languages": [{"language": "en", "context": ["zeta"]}],
        "score_thresholds": {"default": 0.42},
        **REQUIRED_KWARGS.get(cls.__name__, {}),
    }


ROUND_TRIP_CLASSES = [
    cls
    for cls in CONCRETE_RECOGNIZER_CLASSES
    if cls.__name__ not in NOT_LOADABLE_AS_PREDEFINED_ENTRY
]


def test_not_loadable_as_predefined_entry_names_only_real_classes():
    """Guard ``NOT_LOADABLE_AS_PREDEFINED_ENTRY`` against stale entries."""
    names = {cls.__name__ for cls in CONCRETE_RECOGNIZER_CLASSES}
    assert NOT_LOADABLE_AS_PREDEFINED_ENTRY <= names


# The specific error each class in NOT_LOADABLE_AS_PREDEFINED_ENTRY raises
# when actually named in a ``type: predefined`` entry -- not "abstract" in
# the ``inspect.isabstract`` sense (none of these three are: each one
# defines concrete, if trivial, ``analyze``/``load`` and can be instantiated
# directly in Python), but structurally unreachable from a predefined
# registry entry, as proven below rather than only documented in the
# set's own comment.
NOT_LOADABLE_AS_PREDEFINED_ENTRY_ERRORS: Dict[str, Tuple[Type[Exception], str]] = {
    "PatternRecognizer": (ValueError, "patterns or with deny list"),
    "ZaPhoneNumberRecognizer": (ValueError, "target_classification"),
}


def test_not_loadable_as_predefined_entry_errors_matches_the_set():
    """Guard ``NOT_LOADABLE_AS_PREDEFINED_ENTRY_ERRORS`` against drift."""
    assert (
        set(NOT_LOADABLE_AS_PREDEFINED_ENTRY_ERRORS) == NOT_LOADABLE_AS_PREDEFINED_ENTRY
    )


@pytest.mark.parametrize("class_name", sorted(NOT_LOADABLE_AS_PREDEFINED_ENTRY_ERRORS))
def test_not_loadable_as_predefined_entry_actually_fails(class_name):
    """Prove each exclusion in ``NOT_LOADABLE_AS_PREDEFINED_ENTRY``, not just document it.

    Builds the smallest possible ``type: predefined`` entry naming the
    class and asserts construction fails with the specific error its
    comment claims -- not merely *an* exception -- so a future change that
    closes the underlying gap (and makes the class constructible this way)
    fails this test instead of leaving a stale exclusion and a stale comment.
    """
    exc_type, message_fragment = NOT_LOADABLE_AS_PREDEFINED_ENTRY_ERRORS[class_name]
    configuration = {
        "global_regex_flags": GLOBAL_REGEX_FLAGS,
        "supported_languages": ["en"],
        "recognizers": [
            {
                "name": f"conf_{class_name}",
                "class_name": class_name,
                "type": "predefined",
                "supported_entity": "TEST",
                "enabled": True,
            }
        ],
    }
    with pytest.raises(exc_type) as exc:
        RecognizerRegistryProvider(
            registry_configuration=configuration
        ).create_recognizer_registry()
    assert message_fragment in str(exc.value) + str(exc.value.__cause__)


@pytest.mark.parametrize("cls", ROUND_TRIP_CLASSES, ids=lambda cls: cls.__name__)
def test_synthetic_entry_round_trips_to_every_concrete_class(
    cls, patched_loads, monkeypatch, caplog
):
    """A synthetic registry entry round-trips to every concrete class.

    Proves, for every concrete recognizer class -- not only the ones shipped
    enabled in ``default_recognizers.yaml`` -- that ``name``, per-language
    ``context``, and ``score_thresholds`` set in a registry entry actually
    reach the constructed instance, not just that the constructor accepts
    the keys (Story 1/2 already covers acceptance at the signature level).

    For a class that does not accept ``context`` (a multi-entity recognizer),
    the entry must still load: the loader drops the key, logs a WARNING
    naming the class, and the instance keeps the base-class default ``[]``.
    """
    _skip_if_optional_dependency_missing(cls)
    for name, value in REQUIRED_ENV.get(cls.__name__, {}).items():
        monkeypatch.setenv(name, value)

    entry = _synthetic_entry(cls)
    configuration = {
        "global_regex_flags": GLOBAL_REGEX_FLAGS,
        "supported_languages": ["en"],
        "recognizers": [entry],
    }

    with caplog.at_level("WARNING", logger="presidio-analyzer"):
        registry = RecognizerRegistryProvider(
            registry_configuration=configuration
        ).create_recognizer_registry()

    instances = [r for r in registry.recognizers if type(r) is cls]
    assert len(instances) == 1, (
        f"{cls.__name__}: expected exactly one constructed instance, got "
        f"{len(instances)}"
    )
    instance = instances[0]

    assert instance.name == f"conf_{cls.__name__}"
    assert instance.supported_language == "en"
    # Mirrors the loader: context is dropped whenever it is unreachable
    # through the **kwargs-forwarding MRO chain, regardless of whether the
    # leaf itself has **kwargs (keeping it in that case is not provably safe
    # -- see test_context_dropped_for_leaf_forwarding_kwargs_to_a_strict_parent
    # in test_recognizers_loader_utils.py).
    accepts_context = "context" in RecognizerListLoader._reachable_init_param_names(cls)
    context_warnings = [
        r.getMessage()
        for r in caplog.records
        if r.levelname == "WARNING"
        and cls.__name__ in r.getMessage()
        and "'context'" in r.getMessage()
    ]
    if not accepts_context or cls.__name__ in CONTEXT_NOT_APPLIED:
        assert instance.context == [], (
            f"{cls.__name__}: does not apply context, so the instance must "
            f"keep the base-class default"
        )
        assert context_warnings, (
            f"{cls.__name__}: context was dropped without a WARNING naming "
            f"the class and the key"
        )
    else:
        assert not context_warnings, (
            f"{cls.__name__}: accepts context but the loader warned anyway"
        )
        assert instance.context == ["zeta"], (
            f"{cls.__name__}: context did not reach the constructed instance"
        )
    assert instance.score_thresholds == {"default": 0.42}


def test_context_not_applied_names_only_real_classes():
    """Guard ``CONTEXT_NOT_APPLIED`` against stale entries."""
    names = {cls.__name__ for cls in CONCRETE_RECOGNIZER_CLASSES}
    assert CONTEXT_NOT_APPLIED <= names


def test_entry_context_reaches_recognizer_for_bare_language_list():
    """Global context is preserved for a single bare-string language."""
    entry_context = ["zeta"]
    configuration = {
        "global_regex_flags": GLOBAL_REGEX_FLAGS,
        "supported_languages": ["en"],
        "recognizers": [
            {
                "name": "CreditCardRecognizer",
                "type": "predefined",
                "enabled": True,
                "supported_languages": ["en"],
                "context": entry_context,
            }
        ],
    }

    registry = RecognizerRegistryProvider(
        registry_configuration=configuration
    ).create_recognizer_registry()
    instance = [
        r for r in registry.recognizers if type(r).__name__ == "CreditCardRecognizer"
    ][0]

    assert instance.context == entry_context


def test_unknown_key_is_not_silent(caplog):
    """An unknown registry key must never be silently dropped.

    The derived schema reports unknown keys in warning mode; strict registries
    reject them before recognizer construction.
    """
    configuration = {
        "global_regex_flags": GLOBAL_REGEX_FLAGS,
        "supported_languages": ["en"],
        "recognizers": [
            {
                "name": "CreditCardRecognizer",
                "type": "predefined",
                "supported_language": "en",
                "no_such_key": 1,
            }
        ],
    }

    raised = False
    with caplog.at_level("WARNING", logger="presidio-analyzer"):
        try:
            RecognizerRegistryProvider(
                registry_configuration=configuration
            ).create_recognizer_registry()
        except ValueError as exc:
            # Only counts if it actually names the unknown key -- an unrelated
            # ValueError must not be mistaken for the gap having been closed.
            # ConfigurationValidator wraps the underlying pydantic
            # ValidationError in a generic "Invalid recognizer registry
            # configuration" ValueError (see its `raise ... from e`); the key
            # name survives only on `__cause__`, not on the wrapper's own
            # message, so both must be checked or this never flips to XPASS.
            if "no_such_key" in str(exc) or "no_such_key" in str(exc.__cause__):
                raised = True
            else:
                raise

    warned = any("no_such_key" in record.getMessage() for record in caplog.records)
    assert raised or warned, (
        "expected 'no_such_key' to raise ValueError or log a WARNING naming "
        "it; today it is silently dropped"
    )


# ---------------------------------------------------------------------------
# Schema default vs constructor default
# ---------------------------------------------------------------------------

# Keys the loader strips from a validated entry before calling the constructor
# (``predefined_to_exclude`` / ``custom_to_exclude`` in ``RecognizerListLoader``),
# so a schema default for one of them can never reach a constructor and is free
# to differ.
REGISTRY_ONLY_FIELDS = {
    "name",  # Registry identity defaults are class-derived, not constructor literals.
    "enabled",
    "type",
    "class_name",
    "score_thresholds",
    "supported_languages",
    "country_code",
}


def _constructor_default(cls: type, param_name: str) -> Any:
    """Default of ``param_name`` in the first ``__init__`` that declares it.

    Walks the MRO the way the loader's reachability check does, stopping at the
    first ``__init__`` that does not forward ``**kwargs``. Returns
    ``inspect.Parameter.empty`` when the parameter is not reachable.
    """
    for klass in cls.__mro__:
        init = klass.__dict__.get("__init__")
        if init is None:
            continue
        try:
            parameters = inspect.signature(init).parameters
        except (TypeError, ValueError):
            return inspect.Parameter.empty
        if param_name in parameters:
            return parameters[param_name].default
        if not any(
            param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters.values()
        ):
            break
    return inspect.Parameter.empty


# Config model paired with the recognizer class it validates entries for.
# Derive every concrete class; custom entries retain explicit pattern validation.
MODEL_CLASS_PAIRS = [
    (CustomRecognizerConfig, PatternRecognizer),
] + [
    (derive_config_model(cls), cls)
    for cls in CONCRETE_RECOGNIZER_CLASSES
]


def _default_drift_cases() -> List[Tuple[type, type, str]]:
    """(model, recognizer class, field) for every comparable default."""
    cases = []
    for model, cls in MODEL_CLASS_PAIRS:
        for field_name, field in model.model_fields.items():
            if field_name in REGISTRY_ONLY_FIELDS:
                continue
            schema_default = field.get_default(call_default_factory=False)
            # A None default is the "not set" marker the loader strips before
            # construction, so it cannot override anything.
            if schema_default is None or schema_default is PydanticUndefined:
                continue
            if _constructor_default(cls, field_name) is inspect.Parameter.empty:
                continue
            cases.append((model, cls, field_name))
    return cases


DEFAULT_DRIFT_CASES = _default_drift_cases()


@pytest.mark.parametrize(
    ("model", "cls", "field_name"),
    DEFAULT_DRIFT_CASES,
    ids=[f"{m.__name__}.{f}" for m, _, f in DEFAULT_DRIFT_CASES],
)
def test_schema_default_matches_constructor_default(model, cls, field_name):
    """A schema default that reaches a constructor must match its default.

    A field whose schema default is not None survives the loader's
    ``exclude_none`` dump, so it is passed to the constructor even when the
    YAML entry omits the key -- overriding the class default with whatever the
    schema happens to say. The two defaults live in different files with
    nothing tying them together, so they drift silently: ``deny_list_score``
    defaulted to 0.0 in the schema against 1.0 on ``PatternRecognizer``, which
    made every YAML-defined deny list score 0.0 and detect nothing.

    Until presence rather than value drives application, the only thing
    keeping the two in step is that they hold the same literal. This asserts
    it.
    """
    schema_default = model.model_fields[field_name].get_default(
        call_default_factory=False
    )
    constructor_default = _constructor_default(cls, field_name)

    assert schema_default == constructor_default, (
        f"{model.__name__}.{field_name} defaults to {schema_default!r} but "
        f"{cls.__name__}.__init__ defaults it to {constructor_default!r}. An "
        f"entry omitting '{field_name}' is built with the schema's value, so "
        f"these must match until application becomes presence-aware"
    )


@pytest.mark.parametrize(
    "model",
    [BaseRecognizerConfig, PredefinedRecognizerConfig],
    ids=lambda model: model.__name__,
)
def test_shared_config_models_declare_no_reaching_defaults(model):
    """The shared models must not default a field that reaches a constructor.

    ``BaseRecognizerConfig`` and ``PredefinedRecognizerConfig`` validate
    entries for every predefined recognizer, so there is no single constructor
    to compare a default against: a non-None default here would be imposed on
    all of them at once. Registry-only keys are exempt because the loader
    strips them before construction.
    """
    offenders = {
        field_name: field.get_default(call_default_factory=False)
        for field_name, field in model.model_fields.items()
        if field_name not in REGISTRY_ONLY_FIELDS
        and field.get_default(call_default_factory=False) is not None
        and field.get_default(call_default_factory=False) is not PydanticUndefined
    }

    assert not offenders, (
        f"{model.__name__} defaults {offenders!r}; a non-None default on a "
        f"shared model is passed to every predefined recognizer whose entry "
        f"omits the key, overriding each class's own default"
    )
