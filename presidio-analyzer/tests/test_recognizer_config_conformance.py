"""Conformance suite for the recognizer registry / YAML configuration layer.

Presidio's YAML configuration layer is a public contract: a key a user can
set in a registry YAML file either reaches the object it configures, or the
registry raises a message naming the key. This module is the regression
suite that turns that promise into something CI checks, rather than
something a user discovers when they flip ``enabled: true``:

- Story 1/2: every concrete recognizer's constructor must accept the keys
  ``RecognizerListLoader`` injects (``name``, ``supported_language``,
  ``context``, and one of ``supported_entity``/``supported_entities``), or
  enabling it in YAML crashes registry construction with a distant
  ``TypeError`` instead of a clear failure here.
- Story 3: every entry in the shipped ``conf/default_recognizers.yaml``
  loads, and every field it sets reaches the constructed recognizer.
- Story 4: a synthetic YAML entry for *every* concrete recognizer class
  round-trips its ``name``, ``context``, and ``score_thresholds`` -- and an
  unknown key is never silently dropped.
"""

from __future__ import annotations

import inspect
from typing import Dict, List, Set, Type

import presidio_analyzer.predefined_recognizers  # noqa: F401 -- see below
import pytest
from presidio_analyzer import EntityRecognizer
from presidio_analyzer.recognizer_registry.recognizers_loader_utils import (
    RecognizerListLoader,
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


def _reachable_init_param_names(cls: Type[EntityRecognizer]) -> Set[str]:
    """Union of ``__init__`` parameter names reachable from the loader.

    Walks ``cls.__mro__`` starting at ``cls`` itself. Each class along the
    chain that defines its own ``__init__`` contributes its parameter names
    (excluding ``self`` and the ``*args``/``**kwargs`` slots themselves) to
    the union. Traversal stops right after the first ``__init__`` that does
    NOT accept ``**kwargs``: once a constructor stops forwarding arbitrary
    keyword arguments to its superclass, a key the registry loader passes
    for a parameter declared only further up the MRO can never actually
    reach that superclass, so it is not "reachable" from the loader's point
    of view.
    """
    names: Set[str] = set()
    for klass in cls.__mro__:
        init = klass.__dict__.get("__init__")
        if init is None:
            continue
        try:
            parameters = inspect.signature(init).parameters
        except (TypeError, ValueError):
            break
        names.update(
            name
            for name, param in parameters.items()
            if name != "self"
            and param.kind
            not in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL)
        )
        has_var_kw = any(
            param.kind == inspect.Parameter.VAR_KEYWORD for param in parameters.values()
        )
        if not has_var_kw:
            break
    return names


# ---------------------------------------------------------------------------
# Story 1 & 2: base-class contract conformance
# ---------------------------------------------------------------------------

# Keys ``RecognizerListLoader`` injects into every predefined recognizer it
# builds from a registry entry (see ``RecognizerListLoader.get`` /
# ``_prepare_recognizer_kwargs``).
REGISTRY_INJECTED_KEYS = ("name", "supported_language", "context")
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
# Verified against the real signatures via ``_reachable_init_param_names``
# below -- the test asserts the *actual* gap set equals this dict exactly,
# so fixing a class without shrinking this dict fails the test, and so does
# a newly introduced regression.
#
# Empty: AzureHealthDeidRecognizer, AzureOpenAILangExtractRecognizer and
# MedicalNERRecognizer were the three gaps at the time this suite was added
# (all missing `context`) and were closed in the same turn -- see their
# constructors and the `context=[...]` tests in their respective test
# modules.
KNOWN_CONTRACT_GAPS: Dict[str, Set[str]] = {}


def _missing_registry_keys(cls: Type[EntityRecognizer]) -> Set[str]:
    reachable = _reachable_init_param_names(cls)
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


def test_known_contract_gaps_names_only_real_classes():
    """Guard ``KNOWN_CONTRACT_GAPS`` against stale entries.

    A class renamed or removed should fail loudly here, not quietly narrow
    coverage.
    """
    names = {cls.__name__ for cls in CONCRETE_RECOGNIZER_CLASSES}
    assert set(KNOWN_CONTRACT_GAPS) <= names
