# Customizing the NLP engine in Presidio Analyzer

Presidio uses NLP engines for two main tasks: NER based PII identification,
and feature extraction for downstream rule based logic (such as leveraging context words for improved detection).
While Presidio comes with an open-source model (the `en_core_web_lg` model from spaCy),
additional NLP models and frameworks could be plugged in, either public or proprietary.
These models can be trained or downloaded from existing NLP frameworks like [spaCy](https://spacy.io/usage/models),
[Stanza](https://github.com/stanfordnlp/stanza) and
[transformers](https://github.com/huggingface/transformers).

In addition, other types of NLP frameworks [can be integrated into Presidio](developing_recognizers.md#machine-learning-ml-based-or-rule-based).

## Setting up a custom NLP model

- [spaCy or stanza](nlp_engines/spacy_stanza.md)
- [transformers](nlp_engines/transformers.md)

## Configure Presidio to use the new model

Configuration can be done in two ways:

- **Via code**: Create an `NlpEngine` using the `NlpEnginerProvider` class, and pass it to the `AnalyzerEngine` as input:

    ```python
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
    from presidio_analyzer.nlp_engine import NlpEngineProvider

    # Create configuration containing engine name and models
    configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "es", "model_name": "es_core_news_md"},
                    {"lang_code": "en", "model_name": "en_core_web_lg"}],
    }

    # Create NLP engine based on configuration
    provider = NlpEngineProvider(nlp_configuration=configuration)
    nlp_engine_with_spanish = provider.create_engine()

    # Pass the created NLP engine and supported_languages to the AnalyzerEngine
    analyzer = AnalyzerEngine(
        nlp_engine=nlp_engine_with_spanish, 
        supported_languages=["en", "es"]
    )

    # Analyze in different languages
    results_spanish = analyzer.analyze(text="Mi nombre es Morris", language="es")
    print(results_spanish)

    results_english = analyzer.analyze(text="My name is Morris", language="en")
    print(results_english)
    ```

- **Via configuration**: Set up the models which should be used in the [default `conf` file](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/conf/default.yaml).

    An example Conf file:

    ```yaml
    nlp_engine_name: spacy
    models:
        -
        lang_code: en
        model_name: en_core_web_lg
        -
        lang_code: es
        model_name: es_core_news_md 
    ner_model_configuration:
    labels_to_ignore:
    - O
    model_to_presidio_entity_mapping:
        PER: PERSON
        LOC: LOCATION
        ORG: ORGANIZATION
        AGE: AGE
        ID: ID
        DATE: DATE_TIME
    low_confidence_score_multiplier: 0.4
    low_score_entity_names:
    - ID
    - ORG
    ```

    The `ner_model_configuration` section contains the following parameters:

  - `labels_to_ignore`: A list of labels to ignore. For example, `O` (no entity) or entities you are not interested in returning.
  - `model_to_presidio_entity_mapping`: A mapping between the transformers model labels and the Presidio entity types.
  - `low_confidence_score_multiplier`: A multiplier to apply to the score of entities with low confidence.
  - `low_score_entity_names`: A list of entity types to apply the low confidence score multiplier to.

    The [default conf file](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/conf/default.yaml) is read during the default initialization of the `AnalyzerEngine`. Alternatively, the path to a custom configuration file can be passed to the `NlpEngineProvider`:

    ```python
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
    from presidio_analyzer.nlp_engine import NlpEngineProvider

    LANGUAGES_CONFIG_FILE = "./docs/analyzer/languages-config.yml"

    # Create NLP engine based on configuration file
    provider = NlpEngineProvider(conf_file=LANGUAGES_CONFIG_FILE)
    nlp_engine_with_spanish = provider.create_engine()

    # Pass created NLP engine and supported_languages to the AnalyzerEngine
    analyzer = AnalyzerEngine(
        nlp_engine=nlp_engine_with_spanish, 
        supported_languages=["en", "es"]
    )

    # Analyze in different languages
    results_spanish = analyzer.analyze(text="Mi nombre es David", language="es")
    print(results_spanish)

    results_english = analyzer.analyze(text="My name is David", language="en")
    print(results_english)
    ```

    In this examples we:
        a. create an `NlpEngine` holding two spaCy models (one in English: `en_core_web_lg` and one in Spanish: `es_core_news_md`).
        b. define the `supported_languages` parameter accordingly.
        c. pass requests in each of these languages.

    !!! note "Note"
        Presidio can currently use one NER model per language via the `NlpEngine`. If multiple are required,
        consider wrapping NER models as additional recognizers ([see sample here](https://github.com/data-privacy-stack/presidio/blob/main/docs/samples/python/example_remote_recognizer.py)).

## Running without an NLP model

The `NoOpNlpEngine` loads no model and does no NLP processing.
It fits deployments in which no recognizer needs the NLP engine: for example, deployments that only use pattern-based recognizers (credit card, IBAN, email, phone number and so on), or recognizers that run their own model.
Without a model, the memory and the time of the NLP step are saved, and this step no longer depends on the length of the text.

To use it, set the NLP engine name to `no_op`. A `model_name` is required for each language, but no model is loaded:

```yaml
nlp_engine_name: no_op
models:
  - lang_code: en
    model_name: no_op
```

This configuration is bundled as `presidio_analyzer/conf/no_op.yaml`. The Presidio Analyzer server uses it when the `NLP_CONF_FILE` environment variable points to it.

In code:

```python
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NoOpNlpEngine

nlp_engine = NoOpNlpEngine(models=[{"lang_code": "en", "model_name": "no_op"}])
analyzer = AnalyzerEngine(nlp_engine=nlp_engine)

results = analyzer.analyze(text="My credit card is 4012888888881881", language="en")
print(results)
```

This setup changes the results in two ways.

**Entities from the NLP model are not detected.** The `SpacyRecognizer` is not loaded. With the default recognizers, `PERSON`, `LOCATION` and `NRP` are no longer detected. A `RecognizerRegistry` that is created in code with a `SpacyRecognizer` is rejected with an error.

**Context words in the text no longer raise scores.** The context-aware enhancer looks for context words in the tokens and lemmas of the text, and the `NoOpNlpEngine` produces none. Each match keeps the score of its pattern. Scores that come from validation, such as a checksum, do not change:

| Text | Entity | Score with the default spaCy engine | Score with `NoOpNlpEngine` |
| --- | --- | --- | --- |
| My driver license is A1234567 | `US_DRIVER_LICENSE` | 0.65 | 0.3 |
| My phone number is 212-555-0198 | `PHONE_NUMBER` | 0.75 | 0.4 |
| My bank account number is 12345678901 | `US_BANK_NUMBER` | 0.4 | 0.05 |
| My passport number is 912803456 | `US_PASSPORT` | 0.4 | 0.05 |
| My credit card is 4012888888881881 | `CREDIT_CARD` | 1.0 | 1.0 |

### Effect on score thresholds

A score threshold that was chosen with context words in mind removes more results with the `NoOpNlpEngine`.
In the table above, a threshold of 0.5 keeps the driver license and the phone number with the spaCy engine, and removes both with the `NoOpNlpEngine`.

Lowering the threshold brings these results back, but it also keeps matches that have no context word at all.
Weak patterns, such as a run of nine digits, match many values that are not PII, so expect more false positives.

Before moving a deployment to the `NoOpNlpEngine`:

- Check the thresholds again on your own data: the analyzer `default_score_threshold`, the `score_thresholds` of each recognizer, and the `score_threshold` passed in requests.
- If the context is known in advance, for example a column name or a form field label, pass it to `analyze` with the `context` parameter. Explicit context still raises scores with the `NoOpNlpEngine`. It applies to all matches in the text.

## Leverage frameworks other than spaCy, Stanza and transformers for ML based PII detection

In addition to the built-in spaCy/Stanza/transformers capabilities, it is possible to create new recognizers which serve as interfaces to other models.
For more information:

- [Remote recognizer documentation](adding_recognizers.md#creating-a-remote-recognizer) and [samples](../samples/python/integrating_with_external_services.ipynb).
- [Flair recognizer example](../samples/python/flair_recognizer.py)

For considerations for creating such recognizers, see the [best practices for adding ML recognizers documentation](developing_recognizers.md#machine-learning--ml--based-or-rule-based).
