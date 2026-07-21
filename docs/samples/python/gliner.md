# Using GLiNER within Presidio

## What is GLiNER

GLiNER is a Named Entity Recognition (NER) model capable of identifying any entity type using a bidirectional transformer encoder (BERT-like). It provides a practical alternative to traditional NER models, which are limited to predefined entities, and Large Language Models (LLMs) that, despite their flexibility, are costly and large for resource-constrained scenarios.

Paper: [GLiNER: Generalist Model for Named Entity Recognition using Bidirectional Transformer](https://arxiv.org/abs/2311.08526)

Since GLiNER takes as input both the sentence/text and entity types, it can be used for zero-shot named entity recognition. This means that it can recognize entities that were not seen during training.

## PII Detection with GLiNER

GLiNER has a trained PII detection model: 🔍 [`urchade/gliner_multi_pii-v1`](https://huggingface.co/urchade/gliner_multi_pii-v1) *(Apache 2.0)*

This model is capable of recognizing various types of *personally identifiable information* (PII), including but not limited to these entity types: `person`, `organization`, `phone number`, `address`, `passport number`, `email`, `credit card number`, `social security number`, `health insurance id number`, `date of birth`, `mobile phone number`, `bank account number`, `medication`, `cpf`, `driver's license number`, `tax identification number`, `medical condition`, `identity card number`, `national id number`, `ip address`, `email address`, `iban`, `credit card expiration date`, `username`, `health insurance number`, `registration number`, `student id number`, `insurance number`, `flight number`, `landline phone number`, `blood type`, `cvv`, `reservation number`, `digital signature`, `social media handle`, `license plate number`, `cnpj`, `postal code`, `passport_number`, `serial number`, `vehicle registration number`, `credit card brand`, `fax number`, `visa number`, `insurance company`, `identity document number`, `transaction number`, `national health insurance number`, `cvc`, `birth certificate number`, `train ticket number`, `passport expiration date`, and `social_security_number`.

## Using GLiNER with Presidio

Presidio has a built-in `EntityRecognizer` for GLiNER: `GLiNERRecognizer`. This recognizer can be used to detect PII entities in text using the GLiNER model.

### Installation

To use GLiNER with Presidio, you need to install the `presidio-analyzer` with the `gliner` extra:

```bash
pip install 'presidio-analyzer[gliner]'
```

### Example

```python
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import GLiNERRecognizer


# Load a small spaCy model as we don't need spaCy's NER
nlp_engine = NlpEngineProvider(
    nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
    }
)

# Create an analyzer engine 
analyzer_engine = AnalyzerEngine(nlp_engine=nlp_engine.create_engine())

# Define and create the GLiNER recognizer
entity_mapping = {
    "person": "PERSON",
    "name": "PERSON",
    "organization": "ORGANIZATION",
    "location": "LOCATION"
}

gliner_recognizer = GLiNERRecognizer(
    model_name="urchade/gliner_multi_pii-v1",
    entity_mapping=entity_mapping,
    flat_ner=False,
    multi_label=True,
    map_location="cpu",
)

# Add the GLiNER recognizer to the registry
analyzer_engine.registry.add_recognizer(gliner_recognizer)

# Remove the spaCy recognizer to avoid NER coming from spaCy
analyzer_engine.registry.remove_recognizer("SpacyRecognizer")

# Analyze text
results = analyzer_engine.analyze(
    text="Hello, my name is Rafi Mor, I'm from Binyamina and I work at Microsoft. ", language="en"
)

print(results)
```

## ONNX Runtime Support

GLiNERRecognizer supports using ONNX Runtime as a backend, which provides better CPU compatibility and can prevent crashes on older CPUs without AVX2 instruction set support (e.g., Intel Sandy Bridge).

### Using ONNX Runtime Backend

To use ONNX Runtime with GLiNER:

```python
from presidio_analyzer.predefined_recognizers import GLiNERRecognizer

# Enable ONNX Runtime backend
gliner_recognizer = GLiNERRecognizer(
    model_name="urchade/gliner_multi_pii-v1",
    entity_mapping=entity_mapping,
    load_onnx_model=True,  # Enable ONNX Runtime
    map_location="cpu",
)
```

**Benefits of using ONNX Runtime:**
- Works on older CPUs without AVX2 support
- Prevents "Illegal instruction (core dumped)" crashes on incompatible hardware
- Can provide better performance on certain CPU architectures

**Note:** Make sure `onnxruntime` is installed when using this feature. It's included in the `gliner` extra dependencies.

## Configuring multiple GLiNER recognizers via YAML

`GLiNERRecognizer` can also be configured through the [recognizer registry YAML configuration](../../analyzer/recognizer_registry_provider.md). You can define **multiple** `GLiNERRecognizer` instances in the same YAML file (e.g. to use different models, entity mappings or thresholds side by side) by giving each entry a unique `name` while pointing `class_name` at `GLiNERRecognizer`:

```yaml
recognizers:
  - name: GLiNERRecognizerMultiPII
    class_name: GLiNERRecognizer
    type: predefined
    supported_language: en
    model_name: "urchade/gliner_multi_pii-v1"
    threshold: 0.4
    entity_mapping:
      person: PERSON
      organization: ORGANIZATION

  - name: GLiNERRecognizerSmall
    class_name: GLiNERRecognizer
    type: predefined
    supported_language: en
    model_name: "gliner-community/gliner_small-v2.5"
    threshold: 0.25
    entity_mapping:
      location: LOCATION
```

- `name` is the instance name used to identify each recognizer (e.g. in `analysis_explanation.recognizer` on results). It must be unique per entry.
- `class_name` tells the loader which Python class to instantiate (`GLiNERRecognizer` in both cases above); it can be omitted when `name` itself is a valid class name and only a single instance is needed.
- Any additional `GLiNERRecognizer` constructor argument (`model_name`, `threshold`, `entity_mapping`, `flat_ner`, `multi_label`, `map_location`, `load_onnx_model`, `onnx_model_file`, ...) can be set per entry.

**Known limitation:** when instances are configured with *different* `entity_mapping` values (as in the example above), requested entity types are currently appended as ad-hoc GLiNER labels to every selected instance, not just the one whose `entity_mapping` declares them. This can let an entity type "leak" into a recognizer that wasn't configured for it and get evaluated against that recognizer's threshold instead of the intended one — see [#1760](https://github.com/microsoft/presidio/issues/1760#issuecomment-4845372536) for a worked repro. A fix (an opt-out `include_requested_entities_as_labels` flag) is proposed in [#2154](https://github.com/microsoft/presidio/pull/2154); until it merges, be cautious relying on strict per-instance entity isolation when thresholds differ meaningfully between instances.

