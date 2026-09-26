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

## Enabling country-specific recognizers on the default English image

The published `presidio-analyzer` image (`ghcr.io/data-privacy-stack/presidio-analyzer`)
loads only the English NLP model and uses
[`default_recognizers.yaml`](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/conf/default_recognizers.yaml)
with top-level `supported_languages: [en]`.

Several country-specific pattern recognizers are registered for their **native language only**,
for example `ItFiscalCodeRecognizer` (`IT_FISCAL_CODE`, `it`), `EsNifRecognizer` (`ES_NIF`, `es`)
and `PlPeselRecognizer` (`PL_PESEL`, `pl`). These recognizers are pattern- and checksum-based and do
not need an Italian, Spanish or Polish NLP model, but they will not run for `language: en`
because the registry only attaches them to their native language code. US, UK, AU and similar
recognizers are already registered with `en` and need no override.

The defaults are kept native-language-only on purpose: loading every country recognizer for `en`
would increase false positives for deployments that never see those identifiers. Enable the
countries you need with an explicit registry override instead.

!!! warning "Unsupported entities produce a warning, not an error"

    Requesting an entity that no recognizer serves for the request language, together with
    entities that are served (for example `entities: ["IT_FISCAL_CODE", "IBAN_CODE"]` on the
    default `en` image), returns the results for the served entities only. The analyzer logs a
    warning (`Entity IT_FISCAL_CODE doesn't have the corresponding recognizer in language : en.
    Ignoring unsupported entities is deprecated and will raise an error in a future version.`)
    but the HTTP response is still `200`. Only when *none* of the requested entities can be served
    does `/analyze` fail with `No matching recognizers were found to serve the request.`
    Use `GET /supportedentities?language=en` (or `AnalyzerEngine.get_supported_entities`) to
    confirm that an entity is served before relying on it. See
    [issue #2256](https://github.com/data-privacy-stack/presidio/issues/2256).

### Override with `RECOGNIZER_REGISTRY_CONF_FILE`

The analyzer server (`presidio-analyzer/app.py`) reads its configuration paths from the
environment variables `ANALYZER_CONF_FILE`, `NLP_CONF_FILE` and `RECOGNIZER_REGISTRY_CONF_FILE`.
`RECOGNIZER_REGISTRY_CONF_FILE` **replaces** the whole registry configuration; it does not merge a
single recognizer into the defaults. Start from a full copy of `default_recognizers.yaml` and change
only the entries you need.

1. Copy `presidio-analyzer/presidio_analyzer/conf/default_recognizers.yaml` and set
   `supported_languages` to `en` for each recognizer you want on the English image:

    ```yaml
    supported_languages:
      - en
    global_regex_flags: 26

    recognizers:
      # ... other recognizers unchanged ...

      - name: ItFiscalCodeRecognizer
        supported_languages:
        - en
        type: predefined
        country_code: it
    ```

    Keep `country_code: it` so [filtering by country](filtering_by_country.md) still works.
    Listing `it` next to `en` on the recognizer is harmless but has no effect on the default
    image: requests with `language: it` are still rejected, because the registry and the NLP
    engine only support `en`. To serve Italian requests as well, configure the analyzer and NLP
    engine for `it` (see [languages](languages.md)); adding `it` to the registry's top-level
    `supported_languages` alone makes the analyzer fail at startup with a
    "supported languages have to be consistent" error.

2. Mount the file into the container and point the server at it:

    ```sh
    docker run -d -p 5002:3000 \
      -v "$(pwd)/recognizers.yaml:/app/recognizers.yaml:ro" \
      -e RECOGNIZER_REGISTRY_CONF_FILE=/app/recognizers.yaml \
      ghcr.io/data-privacy-stack/presidio-analyzer:latest
    ```

3. Verify that the entity is now served for `en`:

    ```sh
    curl -s "http://localhost:5002/supportedentities?language=en"

    curl -s http://localhost:5002/analyze \
      -H "Content-Type: application/json" \
      -d '{"text":"codice fiscale RSSMRA85M01H501Q","language":"en","entities":["IT_FISCAL_CODE"]}'
    ```

    `IT_FISCAL_CODE` appears in the supported entities list and the fiscal code is returned with
    score `1.0` (omocodic codes such as `RSSMRA85M01H50MI` are detected as well). A code with an
    invalid check character is still reported, but at the pattern score of `0.3`, so integrations
    that apply a score threshold should expect the two cases to differ.

When embedding `AnalyzerEngine` directly, load the same file with `RecognizerRegistryProvider` as
shown at the top of this page, or pass it as `recognizer_registry_conf_file` to
[`AnalyzerEngineProvider`](analyzer_engine_provider.md).
