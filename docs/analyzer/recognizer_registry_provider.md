# Customizing recognizer registry from file
To load recognizers from file, use `RecognizerRegistryProvider` to instantiate the recognizer registry and then pass it through to the analyzer engine:

```python
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

recognizer_registry_conf_file = "./analyzer/recognizers-config.yml"

provider = RecognizerRegistryProvider(
                conf_file=recognizer_registry_conf_file
            )
registry = provider.create_recognizer_registry()
analyzer = AnalyzerEngine(registry=registry)

results = analyzer.analyze(text="My name is Morris", language="en")
print(results)
```

## Shared construction

`RecognizerRegistryProvider`, `RecognizerListLoader.get`,
`RecognizerRegistry.add_recognizers_from_yaml`, and
`RecognizerRegistry.add_pattern_recognizer_from_dict` now use the same
`RecognizerFactory`. The legacy method names and signatures remain available.
The YAML method supports predefined recognizers as well as custom patterns.

The add methods validate the entire addition and reject duplicate identities
against the current registry before constructing any new recognizer. A construction
failure leaves the registry unchanged. They use the registry's languages and regex
flags when the file omits those settings; explicit file settings take precedence.
Entries with no language expand across the registry languages (the old add path
created only an English recognizer). Omitted custom names default to
`PatternRecognizer`; name multiple custom entries explicitly to avoid collisions.
Unlike the old pattern-only add path, configured languages are now filtered.
For example, create `RecognizerRegistry(supported_languages=["en", "de"])` before
adding English and German entries without a top-level language declaration.

For compatibility, the add methods still accept empty additions and unused
top-level file metadata, now warning about ignored keys. `strict: true` rejects
that metadata. In particular `supported_countries` in older example files is not
a registry configuration filter; use the existing country-filtering APIs.
Complete provider configurations still require a nonempty recognizer list and
reject unknown top-level keys.

Global context on a single-language entry now reaches that recognizer whether the
language is a string or a language/context mapping. This fixes previously ignored
context and can increase scores; the existing analysis explanation records the
context contribution. Unsupported context on multi-entity recognizers remains
ignored with a warning.

Advanced callers can separate normalization from loading:

```python
from presidio_analyzer.recognizer_registry import RecognizerFactory

specs = RecognizerFactory.create_specs(
    {"recognizers": [{"class_name": "CreditCardRecognizer"}]}
)
# No recognizers, models or tokenizers have been constructed yet.
recognizers = RecognizerFactory.build_all(specs)
```

`RecognizerSpec` contains one language, accepted constructor kwargs and present
post-construction registry overrides. The existing
`ConfigurationValidator.validate_recognizer_registry_configuration` still returns
a dictionary for compatibility.

Constructor-derived `patterns` can also customize a predefined
`PatternRecognizer` subclass. Set `type: predefined` and select the class with
`class_name` (or the legacy class-as-name field) to retain its checksum and
invalidation hooks. Definitions use the same `name`, `regex`, and `score` fields
as custom recognizers and are converted to `Pattern` objects. Structure and
syntax are checked before any recognizer is loaded. This does not alter shipped
patterns or scores unless the configuration explicitly overrides them. Configured
patterns replace, rather than extend, the class's default list. Without explicit
`type: predefined`, patterns/deny-lists still infer custom type, even when
`class_name` metadata is present. This preserves existing configuration meaning.

## Validate without loading models

```python
from presidio_analyzer.input_validation import validate_registry_config

errors = validate_registry_config("recognizers.yaml", strict=True)
for error in errors:
    print(error.path, error.code, error.message)
```

The function accepts a file path or a complete registry dictionary and returns
`list[ConfigError]`; an empty list means valid configuration. It checks the same
schemas and normalized specs as construction, including regex syntax and duplicate
identities, without constructing recognizers, tokenizers or external models.
It does not check model availability, credentials, external service settings or
whether opaque library options are accepted by a particular library version.

`path` is a tuple of keys and zero-based list indices, such as
`("recognizers", 0, "model_kwargs")`. `code` is a diagnostic category and `message`
does not include input values or arbitrary custom-validator exception text.
Use `path` for original-file locations; identity messages do not repeat entry
numbers that could refer to a separately validated subset.
Repeated-model errors point to an instance that still needs an explicit name.
Independent invalid entries are reported together. Built-in errors include
unknown-key/class suggestions, missing settings, option collisions and thresholds;
untrusted custom-validator messages become a generic diagnostic.

Missing files, malformed YAML and invalid roots produce diagnostics rather than
loading the shipped defaults. `strict=None` keeps the file's policy; `strict=True`
rejects unknown recognizer keys. Without strict mode, deprecated/ignored keys still
emit compatibility warnings and are not returned as errors. Unexpected programming
exceptions are not swallowed.

## Editor schema and generated key reference

The [generated accepted-key reference](recognizer_config_reference.md) follows
the constructor-derived models and lists every bundled public recognizer.

```python
import json
from pathlib import Path
from presidio_analyzer.input_validation import export_registry_schema

Path("registry.schema.json").write_text(
    json.dumps(export_registry_schema(), indent=2), encoding="utf-8"
)
```

The Draft 2020-12 schema preserves permissive unknown-key handling unless the
configuration contains `strict: true`. Pass `strict=True` to the export function
to require known keys regardless of the file setting. Opaque model-option blocks
remain open dictionaries. Pass application-specific classes using
`recognizer_classes=[MyRecognizer]` to include their derived fields.

JSON Schema checks input shape, not every runtime semantic rule or Pydantic
coercion. Use `validate_registry_config` for duplicate identities, regex syntax,
option collisions and class-local validation. No export or reference-generation
operation loads a model or tokenizer.

Regenerate or check the reference from `presidio-analyzer`:

```bash
uv run python ../docs/samples/python/generate_recognizer_config_reference.py
uv run python ../docs/samples/python/generate_recognizer_config_reference.py --check
uv run python ../docs/samples/python/recognizer_config_workflows.py --schema
```

## In-process HTTP workflow

The workflow sample can also exercise the real Analyzer and Anonymizer Flask
routes in-process, without Docker or network calls. It loads and edits analyzer
YAML, verifies single/batch detection and request-level threshold overrides in
both directions, then passes the returned JSON into anonymization. This checks application behavior,
not container image/build configuration.

From a complete checkout with analyzer server/dev dependencies installed:

```bash
cd presidio-analyzer
PYTHONPATH=.:../presidio-anonymizer uv run --no-sync python \
  ../docs/samples/python/recognizer_config_workflows.py --rest
```

## Configuration file structure

```yaml
global_regex_flags: 26

supported_languages: 
  - en

recognizers: 
...
```

The configuration file consists of two parts:

  - `global_regex_flags`: regex flags to be used in regex matching (see [regex flags](https://docs.python.org/3/library/re.html#flags)).
  - `strict`: defaults to `false`. Unknown recognizer keys warn; `true` rejects
    them before model loading, naming the unknown key and accepted alternatives.
  - `supported_languages`: A list of supported languages that the registry will support.
  - `recognizers`: a list of recognizers to be loaded by the recognizer registry. This list consists of two different types of recognizers: 
    - Predefined: A set of already defined recognizer classes in presidio. This includes all recognizers defined in the codebase (along with user defined recognizers) that inherit from EntityRecognizer.
    - Custom: custom created pattern recognizers that are created based on the fields provided in the configuration file.

!!! note "Note"

    supported_languages must be identical to the same field in analyzer_engine

## Recognizer list

The recognizer list comprises of both the predefined and custom recognizers, for example: 

```yaml
...
  - name: CreditCardRecognizer
    supported_languages:
    - language: en
      context: [credit, card, visa, mastercard, cc, amex, discover, jcb, diners, maestro, instapayment]
    - language: es
      context: [tarjeta, credito, visa, mastercard, cc, amex, discover, jcb, diners, maestro, instapayment]
    - language: it
    - language: pl
    type: predefined
    score_thresholds:
      default: 0.4
      CREDIT_CARD: 0.7

  - name: UsBankRecognizer
    supported_languages: 
    - en
    type: predefined

  - name: MedicalLicenseRecognizer
    type: predefined

  - name: ExampleCustomRecognizer
    patterns:
    - name: "zip code (weak)"
      regex: "(\\b\\d{5}(?:\\-\\d{4})?\\b)"
      score: 0.01
    supported_languages:
    - language: en
      context: [zip, code]
    - language: es
      context: [código, postal]
    supported_entity: "ZIP"
    type: custom
    enabled: true

  - name: "TitlesRecognizer"
    supported_language: "en"
    supported_entity: "TITLE"
    deny_list: [Mr., Mrs., Ms., Miss, Dr., Prof.]
    deny_list_score: 1

  - name: "HuggingFace NER"
    type: "predefined"
    class_name: "HuggingFaceNerRecognizer"
    model_name: "dslim/bert-base-NER"
    supported_languages:
      - en
    supported_entities: ["PERSON", "LOCATION", "ORGANIZATION"]
    aggregation_strategy: "simple"
    device: "cpu"
```

### Instance identity

Active recognizers must have distinct `(name, language)` pairs. Validation rejects
duplicates before loading any models. Disabled entries and languages excluded by
the registry do not participate in this check.

Constructors exposing `model_name` support automatic model-specific names.
Recognizers using other identifiers (such as LangExtract's `model_id`) require
explicit names for multiple instances. If the same recognizer class and model
are configured more than once for a language, every entry must have an explicit,
unique name, even when one generated name would not collide with an explicit
name. An omitted model identifier uses the constructor's default for this check.
Empty names are rejected rather than silently replaced by a constructor default.

```yaml
supported_languages: [en]
recognizers:
  - class_name: GLiNERRecognizer
    model_name: urchade/gliner_multi_pii-v1
    name: sensitive
    threshold: 0.3
  - class_name: GLiNERRecognizer
    model_name: urchade/gliner_multi_pii-v1
    name: conservative
    threshold: 0.7
```

The singular `supported_language` selects exactly that language. An explicit empty
`supported_languages: []` creates no instances.

### The recognizer parameters

  - `supported_languages`: A list of supported languages that the analyzer will support. In case this field is missing, a recognizer will be created for each supported language provided to the `AnalyzerEngine`. 
  In addition to the language code, this field also contains a list of context words, which increases confidence in the detection in case it is found in the surroundings of a detected entity (as seen in the credit card example above).
  - `type`: either predefined or custom. When omitted, `patterns` or `deny_list` implies custom; otherwise predefined.
  - `class_name`: selects the predefined Python implementation. When omitted, the legacy `name` field selects it.
  - `name`: instance name used in results. Explicit names are preserved. With `class_name` and no `name`, the name is derived as `ClassName:model_name`, or just `ClassName` for a recognizer without a model. An unnamed custom recognizer defaults to `PatternRecognizer`.
  - `patterns`: a list of objects of type `Pattern` that contains a name, score and regex that define matching patterns.
  - `enabled`: enables or disables the recognizer.
  - `supported_entity`: the detected entity associated by the recognizer.
  - `deny_list`: A list of words to detect, in case the recognizer uses a predefined list of words.
  - `deny_list_score`: confidence score for a term identified using a deny-list. If omitted, defaults to `1.0` (previously this silently defaulted to `0.0` when loaded through `RecognizerRegistryProvider`, which caused deny-list matches to be filtered out by any positive `score_threshold`).
  - `score_thresholds`: optional score thresholds for this recognizer. Use `default` as the recognizer-wide threshold and entity names for overrides. Note that supplying `analyzer_engine.analyze(score_threshold=...)` bypasses recognizer-level thresholds for that request. The precedence is: Presidio Analyzer analyzer.analyze(score_threshold=...) > an entity specific threshold > a recognizer default threshold (`default`) > the Presidio Analyzer `default_score_threshold`.
  - `text_chunker`: configures how long texts are split for NER recognizers (`GLiNERRecognizer`, `HuggingFaceNerRecognizer`). Accepts a dict with `chunker_type` and params. Available types: `character` (default) and `tokenizer` (uses the model's tokenizer for accurate token-based splitting). Example:

    ```yaml
    - name: GLiNERRecognizer
      type: predefined
      model_name: urchade/gliner_multi_pii-v1
      text_chunker:
        chunker_type: tokenizer
        # max_tokens omitted: auto-derived from the model's tokenizer and
        # reduced to reserve room for special tokens ([CLS]/[SEP]). Set it
        # explicitly only if you account for those special tokens yourself.
        overlap_tokens: 32
    ```

!!! tip "Configuration Tip: Agglutinative languages (e.g., Korean)"

    If spaCy-based NER produces noisy or redundant results, you can disable `SpacyRecognizer` and use `HuggingFaceNerRecognizer` as an alternative. Note that `HuggingFaceNerRecognizer` bypasses the spaCy tokenizer alignment mechanism.



    ```yaml
    - name: "SpacyRecognizer"
      type: "predefined"
      class_name: "SpacyRecognizer"
      supported_languages: ["ko"]
      enabled: false
    ```

## Omitted settings and explicit overrides

Omitting a recognizer setting preserves the recognizer constructor's default.
For example, if a recognizer defines its own `score_thresholds`, leaving that key
out of YAML keeps those thresholds. Supplying a mapping overrides them; supplying
`score_thresholds: {}` or `score_thresholds: null` explicitly clears them.
Registry-level defaults, such as `global_regex_flags`, still apply.
The explicit-null reset is specific to `score_thresholds`; null constructor
options continue to use their existing default behavior.

The [configuration workflow script](../samples/python/recognizer_config_workflows.py)
demonstrates creating, editing, and reloading a YAML file, then checking detection
with synthetic data. It needs no downloaded NLP model. From `presidio-analyzer`,
run:

```bash
uv run python ../docs/samples/python/recognizer_config_workflows.py
```

## HuggingFace library options

`HuggingFaceNerRecognizer` accepts two explicit dictionaries:

- `model_kwargs` supplies keyword arguments to `transformers.pipeline`, for
  example `revision`, `token`, or `trust_remote_code`.
- `predict_kwargs` supplies keyword arguments to each pipeline prediction call,
  for example `ignore_labels`, `batch_size`, or `stride`.

```yaml
supported_languages: [en]
recognizers:
  - name: HuggingFaceNerRecognizer
    model_name: example/ner-model
    device: cpu
    model_kwargs:
      revision: your-pinned-model-revision
      trust_remote_code: false
      model_kwargs:
        local_files_only: true
    predict_kwargs:
      ignore_labels: [O]
      batch_size: 1
```

These blocks also work in Python. Their contents must be supported by the
installed Transformers version. A block cannot repeat named recognizer settings
such as `device` or `aggregation_strategy`, or invocation arguments such as
`model`, `tokenizer`, `task`, or `inputs`. `device_map` is rejected because it
conflicts with Presidio's named `device` setting.

Transformers also has its own `model_kwargs` argument for options sent to
`from_pretrained`. The nested dictionary above supplies that argument; block
container names are allowed as library options and do not shadow named settings.

Legacy unsupported flat options remain ignored with a deprecation warning.
When a non-empty `predict_kwargs` block is used, library prediction errors
propagate instead of being converted to an empty detection result.
Existing no-block behavior is unchanged.

The workflow script has an opt-in `--huggingface` scenario using a pinned,
previously downloaded `StanfordAIMI/stanford-deidentifier-base` model. To exercise
the real model without network access, run from `presidio-analyzer`:

```bash
HF_HUB_OFFLINE=1 uv run python ../docs/samples/python/recognizer_config_workflows.py --huggingface
```

## LangExtract provider options

LangExtract recognizers read model and extraction settings from their own file,
selected by `config_path`. Configure `langextract.model.provider.kwargs`,
`langextract.model.provider.language_model_params`, and
`langextract.model.provider.extract_params` there, not as extra registry keys.
Unsupported flat options on `BasicLangExtractRecognizer` are still ignored during
the compatibility period, with a deprecation warning. Its `context` argument is
also not applied; contextual guidance belongs in the prompt file.

The workflow script's `--langextract` option exercises editing this provider file
and loading it through registry YAML. It needs the `langextract` extra but makes
no LLM or service request. Detection with synthetic SDK responses is covered by
the corresponding unit tests.

## Constructor-derived configuration

Recognizer-specific keys are derived from constructor signatures. Adding a new
constructor keyword makes it available in YAML without editing a central
configuration map. Omitted settings are not applied. A per-entry
`global_regex_flags`, when supported by the constructor, takes precedence over
the registry's default flags.

```yaml
strict: true
supported_languages: [en]
recognizers:
  - name: CreditCardRecognizer
    replacement_pairs:
      - ["-", ""]
      - [" ", ""]
```

Without `strict: true`, an unknown recognizer key emits a warning and is ignored.
Legacy flat GLiNER options are the compatibility exception: they are moved into
`model_kwargs` with a deprecation warning. Strict mode requires the named block.
Unknown registry-level keys continue to be errors.

New derived fields are not type-checked against constructor annotations.
Existing HF/GLiNER field coercions and validation are retained by their
class-local rules, so values such as `flat_ner: "false"` keep their old meaning.

Recognizer authors can declare `CONFIG_MODEL` as a Pydantic model containing
cross-field rules. Its validators are combined with the derived fields; use a
`mode="before"` model validator to validate a relationship without maintaining
another copy of constructor fields. Forwarding `**kwargs` exposes reachable
ancestor parameters. A temporary compatibility catch-all that ignores extras
must explicitly declare `CONFIG_LEGACY_KWARGS = "ignore"` instead; model-loading
compatibility shims use `"model_kwargs"`.

`derive_config_model` is available from `presidio_analyzer.input_validation`.
The old per-recognizer config classes remain compatibility imports; new code
should use the derived model. `CONFIG_MODEL_MAP` is deprecated and no longer
controls construction.
