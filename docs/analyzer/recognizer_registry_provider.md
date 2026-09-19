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

### The recognizer parameters

  - `supported_languages`: A list of supported languages that the analyzer will support. In case this field is missing, a recognizer will be created for each supported language provided to the `AnalyzerEngine`. 
  In addition to the language code, this field also contains a list of context words, which increases confidence in the detection in case it is found in the surroundings of a detected entity (as seen in the credit card example above).
  - `type`: this could be either predefined or custom. As this is optional, if not stated otherwise, the default type is custom.
  - `name`: Different per the type of the recognizer. For predefined recognizers, this is the class name as defined in presidio, while for custom recognizers, it will be set as the name of the recognizer.
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

## Enabling country-specific pattern recognizers on the default English image

The published `presidio-analyzer` image (for example
`ghcr.io/data-privacy-stack/presidio-analyzer`) loads only the English NLP
model and uses
[`default_recognizers.yaml`](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/conf/default_recognizers.yaml)
with top-level `supported_languages: [en]`.

Many country-specific pattern recognizers are registered for their **native
language only**. Examples from the default registry:

| Recognizer | Entity | Default `supported_languages` |
| --- | --- | --- |
| `ItFiscalCodeRecognizer` | `IT_FISCAL_CODE` | `it` |
| `EsNifRecognizer` | `ES_NIF` | `es` |
| `PlPeselRecognizer` | `PL_PESEL` | `pl` |

Those recognizers are pattern- and checksum-based: they do **not** need an
Italian/Spanish/Polish NLP model. They still will not run when the request
`language` is `en`, because the registry only attaches them to their native
language code.

US, UK, AU, and similar recognizers are already registered with `en`, so they
work on the default image without an override.

!!! warning "Unsupported entities can be skipped silently"

    On the default `en` image, requesting only `IT_FISCAL_CODE` fails with
    `No matching recognizers were found to serve the request.` Requesting it
    **together with** a supported entity (for example `IBAN_CODE`) can return
    HTTP 200 with results for the supported entities only — `IT_FISCAL_CODE` is
    omitted with no error. Integrations that mix entity lists should enable the
    recognizer via the override below (or treat mixed lists carefully). See
    [issue #2256](https://github.com/data-privacy-stack/presidio/issues/2256).

Defaults stay native-language-only on purpose: loading every country
recognizer for `en` would increase false positives for operators who never see
that country's identifiers. Prefer an explicit registry override for the
countries you need.

### Override with `RECOGNIZER_REGISTRY_CONF_FILE`

The analyzer server reads configuration from environment variables (see
`presidio-analyzer/app.py`):

| Environment variable | Role |
| --- | --- |
| `RECOGNIZER_REGISTRY_CONF_FILE` | Path to the recognizer registry YAML |
| `ANALYZER_CONF_FILE` | Path to the analyzer engine YAML |
| `NLP_CONF_FILE` | Path to the NLP engine YAML |

`RECOGNIZER_REGISTRY_CONF_FILE` **replaces** the registry configuration; it is
not a merge of a single recognizer into the defaults. Start from a full copy of
`default_recognizers.yaml`, then change only the entries you need.

#### 1. Change the recognizer entry

Copy
`presidio-analyzer/presidio_analyzer/conf/default_recognizers.yaml`
and set `supported_languages` to include `en` for each pattern recognizer you
want on the English image:

```yaml
  - name: ItFiscalCodeRecognizer
    supported_languages:
    - en
    type: predefined
    country_code: it
```

You can list both `en` and `it` if the same deployment also serves Italian
(`language: it`) requests. Keep `country_code: it` unchanged so country
filtering still works (see [Filtering recognizers by country](filtering_by_country.md)).

Apply the same pattern to other native-language-only country recognizers as
needed (for example `ItVatCodeRecognizer`, `EsNifRecognizer`).

#### 2. Point the Docker image at the file

```sh
# Assume ./recognizers.yaml is your edited copy of default_recognizers.yaml
docker run -d -p 5002:3000 \
  -v "$(pwd)/recognizers.yaml:/app/recognizers.yaml:ro" \
  -e RECOGNIZER_REGISTRY_CONF_FILE=/app/recognizers.yaml \
  ghcr.io/data-privacy-stack/presidio-analyzer:latest
```

#### 3. Verify

```sh
curl -s http://localhost:5002/analyze \
  -H "Content-Type: application/json" \
  -d '{"text":"codice fiscale RSSMRA85M01H501Q","language":"en","entities":["IT_FISCAL_CODE"]}'
```

You should receive an `IT_FISCAL_CODE` result. Check
`GET /supportedentities?language=en` as well — `IT_FISCAL_CODE` should appear
after the override.

### Python / SDK equivalent

When embedding `AnalyzerEngine` (for example in LiteLLM), load the same YAML
with `RecognizerRegistryProvider`:

```python
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

provider = RecognizerRegistryProvider(
    conf_file="./recognizers.yaml"  # copy of default_recognizers.yaml with en
)
registry = provider.create_recognizer_registry()
analyzer = AnalyzerEngine(registry=registry)

results = analyzer.analyze(
    text="codice fiscale RSSMRA85M01H501Q",
    language="en",
    entities=["IT_FISCAL_CODE"],
)
print(results)
```

You can also pass `recognizer_registry_conf_file` to
[`AnalyzerEngineProvider`](analyzer_engine_provider.md).
