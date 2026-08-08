# Configuration-path testing for recognizers

Read this when reviewing (or writing) the required configuration-path test for a
new or changed recognizer.

## Why this test is mandatory

A recognizer has three construction paths:

1. Direct: `MyRecognizer()` in Python.
2. Registry: `registry.add_recognizer(MyRecognizer())`.
3. Configuration: an entry in a YAML config, loaded by
   `RecognizerRegistryProvider`.

Path 3 is the one real users take to enable a predefined recognizer — they flip
`enabled: true` in a registry YAML. Most predefined recognizers ship
`enabled: false`, so the default test suite never exercises path 3. A recognizer
can pass every direct-construction test and still be unreachable, or crash the
entire registry, the moment someone enables it.

## What the test catches that Python-only tests cannot

- **Constructor signatures incompatible with the keys the loader passes.** The
  loader forwards YAML keys (`name`, `supported_entity`, `context`, ...) into
  `__init__`. A recognizer whose `__init__` doesn't accept `name` raises
  `TypeError: __init__() got an unexpected keyword argument 'name'` — and because
  it happens during registry construction, it takes down every other recognizer
  too.
- **Class-name typos and missing `__init__.py` exports.** The loader resolves the
  class by name; a missing export fails only on the configuration path.
- **`country_code` mismatch** between the class attribute and the YAML entry.
- **Class-level defaults** (thresholds, context) that configuration silently
  discards because the loader sets them after construction instead of passing
  them to `__init__`.
- **Language-filter exclusion.** The top-level `supported_languages` key defaults
  to `["en"]` and acts as a global filter. A recognizer declaring only `de` loads
  nothing, with no error or warning.

## Template

```python
def test_recognizer_loads_and_detects_when_enabled_in_yaml(tmp_path):
    """Detection must work through the path users actually configure."""
    conf = tmp_path / "recognizers.yaml"
    conf.write_text(
        """
supported_languages:
  - en
recognizers:
  - name: MyRecognizer
    supported_languages:
      - en
    type: predefined
    enabled: true
    country_code: us
"""
    )
    registry = RecognizerRegistryProvider(
        conf_file=conf
    ).create_recognizer_registry()
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=nlp_engine)

    results = analyzer.analyze("Member ID ABC123456", language="en")

    assert [result.entity_type for result in results] == ["MY_ENTITY"]
```

## Review notes

- If the recognizer supports only non-English languages, the test's top-level
  `supported_languages` must list those languages, and the PR description should
  state the required top-level languages so users know to set them.
- The assertion should check the entity is actually returned (detection), not
  merely that the registry built without raising. A recognizer that loads but
  detects nothing is still broken.
- One good configuration-path test per new recognizer is enough. It complements,
  not replaces, the direct-construction parametrized tests that cover
  true/false positives and boundaries.
