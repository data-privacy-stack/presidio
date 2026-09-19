# Filtering recognizers by country

Many Presidio deployments only care about a subset of the world's PII —
e.g. a US-only healthcare app, or an EU-only data pipeline. Loading every
predefined country-specific recognizer in those scenarios means more
false positives, more memory, and more noise in the analyzer output.

`RecognizerRegistry.load_predefined_recognizers` accepts an optional
`countries` argument that narrows the country-specific recognizers to
the subset you care about, while always preserving locale-agnostic
recognizers (credit cards, emails, URLs, IBAN, dates, crypto, NER, NLP
engine recognizers, third-party integrations, …).

## Quick example

```python
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry

registry = RecognizerRegistry()
registry.load_predefined_recognizers(languages=["en"], countries=["us", "uk"])

analyzer = AnalyzerEngine(registry=registry)
```

The registry above contains all locale-agnostic recognizers (e.g. credit
card, email, URL) plus US- and UK-specific recognizers (US SSN, UK NHS,
UK NINO, …) — but excludes German, Spanish, Indian, Italian, Korean,
Polish, Singaporean, Swedish, Thai, Turkish, and other country
recognizers.

The same filter can be set globally in YAML, mirroring how
`supported_languages` works:

```yaml
supported_languages: ["en"]
supported_countries: ["us", "uk"]
recognizers:
  # ...
```

When the registry is built from a YAML file, this top-level
`supported_countries` is applied automatically inside the loader; you
don't need to pass `countries=` again from Python.

!!! note "Country filter ≠ request language"

    `supported_countries` / `countries=` controls **which country-tagged
    recognizers are loaded**. Separately, each recognizer's
    `supported_languages` controls **which request `language` values it
    serves**. Several pattern recognizers (Italian, Spanish, Polish, …) ship
    with a native language code only, so they stay inactive on the default
    `en` image even when their country is included. To run them under
    `language: en`, override the registry — see
    [Enabling country-specific pattern recognizers on the default English image](recognizer_registry_provider.md#enabling-country-specific-pattern-recognizers-on-the-default-english-image).

## How the filter works

A recognizer can be tagged with a country in two ways, reconciled at
construction time:

- **Class-level `COUNTRY_CODE`** — the canonical declaration for
  predefined recognizers (`UsSsnRecognizer.COUNTRY_CODE = "us"`, …).
- **Constructor `country_code=` kwarg** — for *custom* recognizers
  without a subclass, or YAML `type: custom` entries that flow through
  `PatternRecognizer.from_dict`. This is the path used by the
  no-code/YAML route.

If both are set, they must agree (case-insensitively); a constructor
value that conflicts with `COUNTRY_CODE` raises `ValueError` so a
predefined Polish-tax-ID recognizer can't be silently re-tagged as
British. The filter then reads the resolved tag through two instance
methods on `EntityRecognizer`:

- `recognizer.country_code()` returns the lower-cased ISO code, or
  `None` if the recognizer is locale-agnostic.
- `recognizer.is_country_specific()` is the named predicate equivalent
  to `country_code() is not None`.

To introspect a class without instantiating, read the
`COUNTRY_CODE` ClassVar directly (e.g. `UsSsnRecognizer.COUNTRY_CODE`);
the methods themselves are instance methods so they can also surface
constructor-tagged custom recognizers.

The filter has a single rule:

| Recognizer's `country_code()` | `countries=None` | `countries=["us"]` | `countries=["us", "uk"]` | `countries=[]` |
| --- | --- | --- | --- | --- |
| `None` (locale-agnostic) | ✅ kept | ✅ kept | ✅ kept | ✅ kept |
| `"us"` | ✅ kept | ✅ kept | ✅ kept | ❌ dropped |
| `"uk"` | ✅ kept | ❌ dropped | ✅ kept | ❌ dropped |
| `"de"` | ✅ kept | ❌ dropped | ❌ dropped | ❌ dropped |

Code comparison is **case-insensitive**: `"US"`, `"Us"`, `"us"` all work.

## Declaring a country on your own recognizers

There are three equivalent paths, pick whichever fits your code shape.
All three end up at the same `self._country_code` and are filtered the
same way.

### 1. Subclass with a class-level `COUNTRY_CODE` (preferred for shared code)

This is the path used by every predefined country-specific recognizer
in Presidio (`UsSsnRecognizer`, `UkNinoRecognizer`, `EsNifRecognizer`,
…). Best when your recognizer lives in code and you want the country
tag visible at the class definition for review:

```python
from presidio_analyzer import Pattern, PatternRecognizer


class BrCpfRecognizer(PatternRecognizer):
    """Recognize Brazilian CPF numbers."""

    COUNTRY_CODE = "br"

    PATTERNS = [
        Pattern("BR CPF (medium)", r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", 0.5),
    ]

    def __init__(self):
        super().__init__(
            supported_entity="BR_CPF",
            patterns=self.PATTERNS,
            supported_language="pt",
        )
```

`BrCpfRecognizer().country_code()` returns `"br"` and the registry's
country filter treats it the same as predefined country-specific
recognizers.

### 2. Constructor `country_code=` (preferred for one-offs)

If you don't want to subclass — e.g. you're constructing a one-off
`PatternRecognizer` for an Armenian national ID — pass `country_code`
to the constructor:

```python
from presidio_analyzer import Pattern, PatternRecognizer

am_recognizer = PatternRecognizer(
    supported_entity="AM_NATIONAL_ID",
    name="AmNationalIdRecognizer",
    patterns=[Pattern("AM 10-digit", r"\b\d{10}\b", 0.5)],
    country_code="am",
)
assert am_recognizer.country_code() == "am"
```

This also covers `PatternRecognizer.from_dict({"country_code": "am",
...})`, so any tooling that round-trips recognizer dicts (logs,
serialization, recognizer-store backends, …) preserves the tag.

### 3. YAML `type: custom` with `country_code:` (no-code path)

YAML custom-recognizer entries forward `country_code` straight through
to `PatternRecognizer.__init__` via `from_dict`, so the no-code path
gets the same tagging without writing a single line of Python:

```yaml
recognizers:
  - name: AmNationalIdRecognizer
    type: custom
    supported_entity: AM_NATIONAL_ID
    supported_languages:
      - language: en
    country_code: am
    patterns:
      - name: "AM 10-digit"
        regex: '\b\d{10}\b'
        score: 0.5
```

Loading this registry with `supported_countries: ["am"]` (or the
Python-side `countries=["am"]`) keeps the recognizer; filtering to a
different country drops it.

### Combining paths

If you subclass *and* pass `country_code=` to the constructor, the two
must agree — passing a different value raises `ValueError`. This means
a predefined `UsSsnRecognizer` can never be silently re-tagged via the
constructor, and a YAML `country_code:` on a `type: predefined` entry
is cross-checked against the class attribute at load time (see the
"Annotating predefined recognizers in YAML" section below).

## Annotating predefined recognizers in YAML

When you wire up the registry from a YAML file (the no-code path), you
can — and should — also declare the country tag next to each predefined
country-specific entry. This is purely advisory metadata that documents
the entry for human readers; the class-level `COUNTRY_CODE` remains the
source of truth, and the loader cross-checks the two and refuses to
load on a mismatch:

```yaml
recognizers:
  - name: UsSsnRecognizer
    supported_languages:
      - en
    type: predefined
    country_code: us       # must match UsSsnRecognizer.COUNTRY_CODE

  - name: UkNinoRecognizer
    supported_languages:
      - en
    type: predefined
    country_code: uk

  - name: CreditCardRecognizer
    type: predefined
    # no country_code: locale-agnostic
```

If you change one without the other, the registry will raise
`ValueError` at load time naming both the YAML value and the class
attribute, so the misconfiguration is fixable from the error message
alone.

## When to leave `COUNTRY_CODE` unset

Some PII patterns are not anchored to a single country and should
remain locale-agnostic:

- Credit card numbers, email addresses, URLs, MAC addresses, crypto
  wallet addresses, dates, phone numbers (PhoneNumbers cover multiple
  countries via `phonenumbers`), …
- IBAN — geographically European-ish but not anchored to one country.
- Generic NER models (spaCy, Stanza, transformer-based recognizers).

Leave `COUNTRY_CODE` unset (it inherits the default `None` from
`EntityRecognizer`) for these. They will always be loaded and the
country filter will not touch them.

## Backwards compatibility

The filter is fully backwards compatible:

1. **Default behavior is unchanged.** Calling
   `load_predefined_recognizers()` without `countries` (or with
   `countries=None`) loads every predefined recognizer exactly as before.
2. **Untagged custom recognizers continue to work.** Any recognizer you
   have already deployed that does not declare `COUNTRY_CODE` is treated
   as locale-agnostic and is never filtered out — regardless of the
   requested countries. The filter only excludes recognizers that have
   explicitly opted in via the class attribute.
3. **Predefined recognizers are pre-tagged.** Every recognizer under
   `presidio_analyzer.predefined_recognizers.country_specific.<country>`
   ships with its `COUNTRY_CODE` set to the appropriate ISO code, so
   `countries=["us"]` works on a fresh install with no further setup.

## Debugging

If you pass `countries=["br"]` and your custom Brazilian recognizer
disappears, the most likely cause is that the recognizer hasn't
declared `COUNTRY_CODE = "br"`. Two diagnostic helpers:

- `registry.get_country_codes()` returns the sorted list of country
  codes currently represented in the registry. If `"br"` is missing, no
  recognizer is tagged.
- The filter logs a `WARNING` whenever a requested country matches no
  recognizer in the input set, with a hint to set `country_code` on
  custom recognizers.

```python
import logging
logging.getLogger("presidio-analyzer").setLevel(logging.WARNING)

registry = RecognizerRegistry()
registry.load_predefined_recognizers(countries=["br"])
# WARNING ... Country filter: no recognizer matched country_code='br'.
#         If you have custom recognizers for 'br', set country_code='br'
#         on them to include them in country-filtered loads.
print(registry.get_country_codes())
# ['au', 'ca', 'de', 'es', 'fi', 'in', 'it', 'kr', 'ng', 'pl', 'se',
#  'sg', 'th', 'tr', 'uk', 'us']
```
