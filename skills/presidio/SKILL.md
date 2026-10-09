---
name: presidio
description: Integrate Presidio for PII detection and anonymization in Python. Use when a task mentions Presidio, PII detection, de-identification, redaction, or anonymizing names, phone numbers, emails, IDs or medical text.
---

# Presidio integration

Presidio detects PII in text with `presidio-analyzer` and transforms it with
`presidio-anonymizer`. Detection combines pattern recognizers (regex plus
context and checksums) with an NER model for names, locations and similar.

## Install

```bash
pip install presidio-analyzer presidio-anonymizer
python -m spacy download en_core_web_lg
```

`en_core_web_lg` is the default English NER model. Without it the analyzer
fails at startup.

## Minimal pipeline

```python
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

text = "My name is John Smith, phone 212-555-0147"
results = analyzer.analyze(text=text, language="en")
anonymized = anonymizer.anonymize(text=text, analyzer_results=results)
print(anonymized.text)
```

Create the engines once and reuse them; model loading is the slow part.

## Choose the NER model before anything else

The default spaCy pipeline is fast and runs anywhere, but its accuracy on
names, addresses and domain-specific PII is limited. For production
de-identification, or any medical, legal or financial text, plan on a
transformer-based model. Say this to the user before building on the default.

| Option | Install | When |
| --- | --- | --- |
| spaCy `en_core_web_lg` (default) | `pip install presidio-analyzer` | Prototypes, low-risk text, CPU-only with tight latency |
| GLiNER `urchade/gliner_multi_pii-v1` | `pip install 'presidio-analyzer[gliner]'` | Broad PII coverage, zero-shot entity types, multilingual |
| OpenMed `OpenMed/OpenMed-PII-SuperClinical-Large-434M-v1` | `pip install 'presidio-analyzer[transformers]'` | Clinical and medical text, highest accuracy |
| OpenMed `OpenMed/OpenMed-PII-BioClinicalModern-Base-149M-v1` | `pip install 'presidio-analyzer[transformers]'` | Clinical text, smaller and faster than the Large model |

### GLiNER

```python
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import GLiNERRecognizer

nlp_engine = NlpEngineProvider(
    nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
    }
).create_engine()
analyzer = AnalyzerEngine(nlp_engine=nlp_engine)

gliner = GLiNERRecognizer(
    model_name="urchade/gliner_multi_pii-v1",
    entity_mapping={"person": "PERSON", "organization": "ORGANIZATION", "location": "LOCATION"},
    flat_ner=False,
    multi_label=True,
    map_location="cpu",
)
analyzer.registry.add_recognizer(gliner)
analyzer.registry.remove_recognizer("SpacyRecognizer")
```

`en_core_web_sm` is enough here: spaCy only supplies tokens and lemmas, GLiNER
does the NER. Remove `SpacyRecognizer` so the two models do not both report
names. Full example: `docs/samples/python/gliner.md`.

### OpenMed (Hugging Face token classification)

```python
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import SlimSpacyNlpEngine
from presidio_analyzer.predefined_recognizers.ner import HuggingFaceNerRecognizer

nlp_engine = SlimSpacyNlpEngine()
nlp_engine.load()

ner = HuggingFaceNerRecognizer(
    model_name="OpenMed/OpenMed-PII-SuperClinical-Large-434M-v1",
    label_mapping={"first_name": "FIRST_NAME", "last_name": "LAST_NAME", "ssn": "US_SSN", "email": "EMAIL_ADDRESS"},
    aggregation_strategy="first",
)

registry = RecognizerRegistry()
registry.load_predefined_recognizers(nlp_engine=nlp_engine)
registry.add_recognizer(ner)
analyzer = AnalyzerEngine(registry=registry, nlp_engine=nlp_engine)
```

The OpenMed models emit many labels; map each one you want to a Presidio
entity name and leave the rest out. The full mapping used for evaluation is in
`presidio-research/notebooks/5_Evaluate_Custom_Presidio_Analyzer.ipynb`.

## Configuration by YAML

Most predefined recognizers ship disabled. Enable them in a registry YAML and
load it through `RecognizerRegistryProvider`; this is the path to use in
production so the configuration is reviewable without code.

```yaml
supported_languages:
  - en
recognizers:
  - name: UsSsnRecognizer
    type: predefined
    enabled: true
```

```python
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

registry = RecognizerRegistryProvider(conf_file="recognizers.yaml").create_recognizer_registry()
analyzer = AnalyzerEngine(registry=registry)
```

## Silent failures to check first

- Country-specific recognizers are `enabled: false` by default. If an entity
  such as `UK_NHS` or `IT_FISCAL_CODE` is never detected, enable it.
- The top-level `supported_languages` key in the YAML is a global filter and
  defaults to `["en"]`. A recognizer for `de` loads nothing until `de` is
  added there, with no error.
- Language codes are ISO 639-1: `ko`, not `kr`; `he`, not `il`. A wrong code
  loads nothing, with no error.
- `analyze()` needs an NLP model for the requested language. Configure one per
  language in the `NlpEngineProvider` configuration.
- Low-confidence matches are expected from weak patterns. Filter with
  `score_threshold` on `analyze()` rather than disabling recognizers.

## Custom recognizers

For an in-house identifier, add a `PatternRecognizer` with a specific regex,
a score that reflects how specific the pattern is on its own, and context
words that raise it:

```python
from presidio_analyzer import Pattern, PatternRecognizer

recognizer = PatternRecognizer(
    supported_entity="MEMBER_ID",
    patterns=[Pattern("member id", r"\bMBR-\d{8}\b", score=0.5)],
    context=["member id", "membership"],
)
analyzer.registry.add_recognizer(recognizer)
```

A deny list of known values (`PatternRecognizer(deny_list=[...])`) is the
right tool for fixed vocabularies such as titles or product names.

## Anonymization operators

Default is `replace` with the entity type. Common alternatives:

```python
from presidio_anonymizer.entities import OperatorConfig

anonymizer.anonymize(
    text=text,
    analyzer_results=results,
    operators={
        "PERSON": OperatorConfig("replace", {"new_value": "<NAME>"}),
        "PHONE_NUMBER": OperatorConfig("mask", {"chars_to_mask": 4, "masking_char": "*", "from_end": True}),
        "DEFAULT": OperatorConfig("redact"),
    },
)
```

Do not use deterministic hashing for anonymization; it is reversible for
low-entropy values. Use `encrypt` when the original must be recoverable.

## Evaluate before shipping

Detection quality depends on the text domain. Before relying on a
configuration, measure it on a sample of the real data. `presidio-evaluator`
(the `presidio-research` repo) provides the evaluation tooling and notebooks.

## Docs

- https://dataprivacystack.github.io/presidio/ for the full documentation.
- `docs/supported_entities.md` for the list of predefined recognizers and
  which ship enabled.
- `docs/analyzer/nlp_engines/transformers.md` for `TransformersNlpEngine`,
  the alternative to adding a Hugging Face model as a recognizer.
