# Using ReDefiNER within Presidio

## What is ReDefiNER

[ReDefiNER](https://github.com/jungroo-ai/redefiner) is an open model (0.8B parameters, Apache 2.0) that finds spans
of text according to a rulebook written in plain English. A rulebook lists entity types, each with a one-line
description, and can add rules, such as what must never be detected. To change what is detected, you edit the
rulebook instead of retraining the model. The model is non-generative: it returns spans of the input text and never
writes new text. It runs on CPU or GPU and supports English only.

A ready-made PII rulebook with 20 entity types is published as
[`jungroo-ai/redefiner-pii`](https://huggingface.co/jungroo-ai/redefiner-pii). Its weights come from
[`jungroo-ai/redefiner-0.8b`](https://huggingface.co/jungroo-ai/redefiner-0.8b).

## Using ReDefiNER with Presidio

[`presidio-redefiner`](https://github.com/Jungroo-AI/presidio-redefiner) is a community plugin that provides a
`ReDefiNERRecognizer` for the analyzer. It is maintained by Jungroo AI Labs, not by the Presidio maintainers.

### Installation

```bash
pip install "presidio-redefiner[anonymizer]"
python -m spacy download en_core_web_sm
```

The first run downloads the model weights (about 0.8 GB) from Hugging Face.

### Example: the ready-made PII rulebook

```python
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_redefiner import ReDefiNERRecognizer

nlp_engine = NlpEngineProvider(
    nlp_configuration={
        "nlp_engine_name": "slim",
        "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
    }
).create_engine()
analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
analyzer.registry.add_recognizer(ReDefiNERRecognizer())

text = "Please call Rosa Diaz on +44 20 7946 0958 or email rdiaz@example.net."
results = analyzer.analyze(text=text, language="en")
print(AnonymizerEngine().anonymize(text=text, analyzer_results=results).text)
# Please call <PERSON> on <PHONE_NUMBER> or email <EMAIL_ADDRESS>.
```

### Example: entities defined by your own rulebook

Pass a rulebook to detect what your own policy describes. In this example the registry holds only this recognizer, so
the rulebook alone decides what is found:

```python
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NoOpNlpEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_redefiner import ReDefiNERRecognizer

policy = """[RULES]
G1 Extract every piece of personal data of the supplied types. Return exact spans from the text.

[TYPE] PERSON
[DESCRIPTION] A person's name, without titles such as "Dr." or "Ms".

[TYPE] EMPLOYEE_ID
[DESCRIPTION] An employee number, such as "E-48213".

[TYPE] SALARY
[DESCRIPTION] A person's pay: salary, bonus or hourly rate, with its currency.

[TYPE] NOT_AN_ENTITY
NE1 Names of teams, departments and products, and the company's own name.
"""

registry = RecognizerRegistry()
registry.add_recognizer(ReDefiNERRecognizer(rulebook=policy, entity_mapping={"EMPLOYEE_ID": "ID"}))
analyzer = AnalyzerEngine(
    registry=registry,
    nlp_engine=NoOpNlpEngine(models=[{"lang_code": "en", "model_name": "no_op"}]),
)

text = "Dr. Maria Okafor (E-40917) joins the Payments team at Acme on a salary of $96,500."
results = analyzer.analyze(text=text, language="en")
print(AnonymizerEngine().anonymize(text=text, analyzer_results=results).text)
# Dr. <PERSON> (<ID>) joins the Payments team at Acme on a salary of <SALARY>.
```

### Notes

- **Entity names.** The recognizer maps the rulebook's types to Presidio entity names where one exists (for example
  `EMAIL` to `EMAIL_ADDRESS`) and keeps other types as they are. `entity_mapping` changes this. The rulebook's own
  type is kept in `recognition_metadata["redefiner_label"]`.
- **Score threshold.** Each result's score is the model's confidence. `min_confidence` (default 0) or the analyzer's
  `score_threshold` drops low-confidence results.
- **Speed and memory.** On CPU, the first call with a rulebook takes several seconds while the rulebook is read; later
  calls with the same rulebook take under a second for short texts. With the ready-made PII rulebook, peak memory on
  CPU is about 3 GB.
- **Accuracy.** Like any recognizer, it can miss personal data or flag text that is not personal. Evaluate it on your
  own data before relying on it.

More options are described in the [plugin's README](https://github.com/Jungroo-AI/presidio-redefiner).
