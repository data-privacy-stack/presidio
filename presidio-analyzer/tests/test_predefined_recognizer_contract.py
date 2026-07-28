"""Contract tests between the registry loader and predefined recognizers.

``RecognizerListLoader`` builds predefined recognizers from YAML by passing the
entry's keys as constructor kwargs. That makes the constructor signature part of
a contract which nothing else enforces: a recognizer can satisfy every one of
its own unit tests -- which instantiate it directly -- and still be impossible
to load from a registry configuration.

The gap is specifically in the *disabled* entries. ``default_recognizers.yaml``
ships ~60 recognizers with ``enabled: false``, and no other test constructs
them, so a broken constructor stays invisible until a user flips the switch.
These tests construct every one of them.
"""

import inspect
from pathlib import Path
from typing import Dict, List

import presidio_analyzer.predefined_recognizers as predefined
import pytest
import yaml
from presidio_analyzer import EntityRecognizer, PatternRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider
from presidio_analyzer.recognizer_registry.recognizers_loader_utils import (
    RecognizerListLoader,
)

# The component root, i.e. the directory that contains the ``presidio_analyzer``
# package. Some shipped entries carry a ``config_path`` that the recognizer
# resolves relative to the current working directory, so the load test runs from
# here -- the same working directory CI uses -- rather than catching the
# resulting error. Catching it would turn a genuinely missing shipped file into
# a passing skip.
PACKAGE_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_CONF = PACKAGE_ROOT / "presidio_analyzer" / "conf" / "default_recognizers.yaml"

# Kwargs ``RecognizerListLoader`` passes to every predefined recognizer it
# builds: ``name`` comes from the YAML entry (or its ``class_name`` alias) and
# ``supported_language`` from the resolved per-language configuration.
LOADER_KWARGS = ("name", "supported_language")

# Entries that cannot load from their shipped configuration even with every
# dependency installed, so the load test below cannot cover them.
#
# ``HuggingFaceNerRecognizer``: ``EntityRecognizer.__init__`` calls ``load()``
# unconditionally and ``load()`` requires ``model_name``, which the shipped
# entry does not supply -- it raises ValueError once ``transformers`` and
# ``torch`` are present. That is a pre-existing defect in the entry, not
# something this contract can assert away, and adding ``model_name`` here would
# make the test download a model. It stays covered by the resolve test.
NOT_LOADABLE_FROM_SHIPPED_ENTRY = {"HuggingFaceNerRecognizer"}

# Entries gated behind an optional dependency, for which refusing to load with an
# actionable ImportError is the intended behavior. The skip is scoped to these
# names rather than to the exception type, so an ImportError from any other entry
# stays a failure instead of a green skip.
OPTIONAL_DEPENDENCY_ENTRIES = {"BasicLangExtractRecognizer"}


def _pattern_recognizer_classes() -> Dict[str, type]:
    """Predefined ``PatternRecognizer`` subclasses, which the YAML loader builds.

    Non-pattern recognizers (NER/LLM/remote wrappers) are excluded: several are
    not registrable from ``default_recognizers.yaml`` and some deliberately fix
    their own display name.
    """
    classes = {}
    for attr in dir(predefined):
        obj = getattr(predefined, attr)
        if not isinstance(obj, type) or not issubclass(obj, EntityRecognizer):
            continue
        if obj in (EntityRecognizer, PatternRecognizer):
            continue
        if issubclass(obj, PatternRecognizer):
            classes[attr] = obj
    return classes


def _yaml_entries() -> List[Dict]:
    """Normalize the shipped recognizer list to dict entries."""
    data = yaml.safe_load(DEFAULT_CONF.read_text(encoding="utf-8"))
    entries = []
    for entry in data["recognizers"]:
        entries.append({"name": entry} if isinstance(entry, str) else dict(entry))
    return entries


def _entry_languages(entry: Dict) -> List[str]:
    """Languages an entry declares, in either supported YAML shape."""
    languages = entry.get("supported_languages")
    if not languages:
        return ["en"]
    if isinstance(languages[0], str):
        return list(languages)
    return [item["language"] for item in languages]


def _entry_id(entry: Dict) -> str:
    return entry.get("class_name") or entry["name"]


PATTERN_CLASSES = _pattern_recognizer_classes()
YAML_ENTRIES = _yaml_entries()
LOADABLE_YAML_ENTRIES = [
    entry
    for entry in YAML_ENTRIES
    if _entry_id(entry) not in NOT_LOADABLE_FROM_SHIPPED_ENTRY
]


def test_default_conf_has_entries():
    """Guard the fixtures themselves: an empty parse would pass everything."""
    assert PATTERN_CLASSES, "no predefined PatternRecognizer subclasses found"
    assert YAML_ENTRIES, "no recognizers parsed from default_recognizers.yaml"


@pytest.mark.parametrize(
    "entry_id",
    sorted(NOT_LOADABLE_FROM_SHIPPED_ENTRY | OPTIONAL_DEPENDENCY_ENTRIES),
)
def test_exclusion_names_a_real_entry(entry_id):
    """An exclusion must still match a shipped entry.

    Keeps the two lists above from rotting: if an entry is renamed, removed, or
    fixed, the stale exclusion fails here instead of silently narrowing
    coverage.
    """
    assert entry_id in {_entry_id(entry) for entry in YAML_ENTRIES}


CONFIG_PATH_ENTRIES = [entry for entry in YAML_ENTRIES if entry.get("config_path")]


@pytest.mark.parametrize("entry", CONFIG_PATH_ENTRIES, ids=_entry_id)
def test_yaml_entry_config_path_points_at_a_shipped_file(entry):
    """A ``config_path`` in a shipped entry must point at a file that ships.

    Asserted directly rather than left to the load test, which skips the entry
    when its optional dependency is absent. A deleted or renamed config file is
    a regression that must fail even in an environment that cannot construct the
    recognizer at all.
    """
    config_path = Path(entry["config_path"])
    resolved = config_path if config_path.is_absolute() else PACKAGE_ROOT / config_path
    assert resolved.is_file(), (
        f"{_entry_id(entry)} declares config_path {entry['config_path']!r}, "
        f"which does not resolve to a file ({resolved})"
    )


@pytest.mark.parametrize("class_name", sorted(PATTERN_CLASSES))
def test_pattern_recognizer_accepts_loader_kwargs(class_name):
    """Constructor must accept every kwarg the YAML loader passes.

    Catches the defect before the recognizer reaches the YAML at all: a class
    added without ``name`` passes its own unit tests, and only fails once
    someone tries to register it.
    """
    parameters = inspect.signature(PATTERN_CLASSES[class_name].__init__).parameters
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in parameters.values()):
        return
    missing = [kwarg for kwarg in LOADER_KWARGS if kwarg not in parameters]
    assert not missing, (
        f"{class_name}.__init__ does not accept {missing}, which "
        f"RecognizerListLoader passes to every predefined recognizer. "
        f"Loading it from a registry YAML raises TypeError."
    )


@pytest.mark.parametrize("entry", YAML_ENTRIES, ids=_entry_id)
def test_yaml_entry_class_resolves(entry):
    """Every shipped entry must name a real recognizer class."""
    RecognizerListLoader.get_existing_recognizer_cls(recognizer_name=_entry_id(entry))


@pytest.mark.parametrize("entry", LOADABLE_YAML_ENTRIES, ids=_entry_id)
def test_yaml_entry_loads_when_enabled(entry, monkeypatch):
    """Every shipped entry must load once ``enabled`` is true.

    ``enabled: false`` is an opt-in switch, not a disclaimer -- an entry that
    cannot be turned on should not be listed.

    Runs from ``PACKAGE_ROOT`` so that a ``config_path`` the recognizer resolves
    against the working directory behaves as it does in CI. A FileNotFoundError
    is therefore a real missing shipped file and is left to fail.
    """
    entry_id = _entry_id(entry)
    entry = dict(entry, enabled=True)
    monkeypatch.chdir(PACKAGE_ROOT)
    configuration = {
        "global_regex_flags": yaml.safe_load(DEFAULT_CONF.read_text(encoding="utf-8"))[
            "global_regex_flags"
        ],
        "supported_languages": _entry_languages(entry),
        "recognizers": [entry],
    }

    try:
        registry = RecognizerRegistryProvider(
            registry_configuration=configuration
        ).create_recognizer_registry()
    except ImportError as exc:
        if entry_id not in OPTIONAL_DEPENDENCY_ENTRIES:
            raise
        pytest.skip(f"{entry_id} needs an optional dependency: {exc}")

    assert registry.recognizers, (
        f"{_entry_id(entry)} is listed in default_recognizers.yaml but loaded "
        f"nothing for languages {_entry_languages(entry)}"
    )


def test_yaml_entry_can_be_renamed_via_class_name():
    """``class_name`` + ``name`` must give the instance the configured name.

    This is the documented reason the loader passes ``name`` at all (see
    ``RecognizerListLoader.get_recognizer_name``), so it is the behavior that
    makes the kwarg contract above load-bearing rather than incidental.
    """
    configuration = {
        "global_regex_flags": 26,
        "supported_languages": ["en"],
        "recognizers": [
            {
                "class_name": "UsSsnRecognizer",
                "name": "MyRenamedSsnRecognizer",
                "supported_languages": ["en"],
                "type": "predefined",
                "country_code": "us",
            }
        ],
    }
    registry = RecognizerRegistryProvider(
        registry_configuration=configuration
    ).create_recognizer_registry()

    assert [r.name for r in registry.recognizers] == ["MyRenamedSsnRecognizer"]
