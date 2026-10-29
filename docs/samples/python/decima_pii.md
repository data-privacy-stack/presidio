# Using decima-pii as an external PII model

## What is decima-pii

[decima-pii](https://huggingface.co/amyrmahdy/decima-pii) *(Apache 2.0)* is a small token-classification model (140M parameters, 148 MB as int8 ONNX) that finds personal data in **Arabic, Persian, Urdu, Turkish and English** text on a CPU, without PyTorch. It also reads numbers written in Arabic-Indic (`٠٥٥…`) and Persian (`۰۹۱۲…`) digits, which Presidio's pattern recognizers detect only inconsistently today (see [#2378](https://github.com/data-privacy-stack/presidio/issues/2378)).

It tags ten types, mapped to Presidio entities in this sample:

| decima-pii | Presidio entity |
| :--- | :--- |
| `PERSON_NAME` | `PERSON` |
| `PHONE` | `PHONE_NUMBER` |
| `EMAIL` | `EMAIL_ADDRESS` |
| `NATIONAL_ID` | `NATIONAL_ID` (any country, e.g. Iran, Saudi Arabia, Qatar, UAE, Pakistan, Turkey) |
| `IBAN` | `IBAN_CODE` |
| `CARD` | `CREDIT_CARD` |
| `PASSPORT` | `PASSPORT` (any country) |
| `ADDRESS` | `LOCATION` |
| `DATE_OF_BIRTH` | `DATE_TIME` |
| `IP_ADDRESS` | `IP_ADDRESS` |

The model is used through the `DecimaPII` class from the `decima-ai` package, which turns the token tags into character spans, keeps spaced numbers such as `5185 5272 2255 5565` as one span, drops spans that cannot be what they claim (a 3-digit phone, an email without `@`), and tags long texts in overlapping windows.

## Installation

```bash
pip install presidio-analyzer presidio-anonymizer decima-ai
```

`decima-ai` brings `onnxruntime`, `tokenizers` (through `transformers`) and `huggingface_hub`; it does not install PyTorch. The model is downloaded from the Hugging Face Hub on first use.

## Example

decima-pii works on the raw text, so it does not need a spaCy model for these languages. This example uses Presidio's `NoOpNlpEngine` to declare the five languages, and registers one recognizer per language, all sharing the same loaded model.

```python
from typing import List, Optional

from decima.pii import DecimaPII
from presidio_analyzer import (
    AnalysisExplanation,
    AnalyzerEngine,
    EntityRecognizer,
    RecognizerRegistry,
    RecognizerResult,
)
from presidio_analyzer.nlp_engine import NlpArtifacts, NoOpNlpEngine
from presidio_anonymizer import AnonymizerEngine

# decima-pii label -> Presidio entity
DECIMA_TO_PRESIDIO = {
    "PERSON_NAME": "PERSON",
    "PHONE": "PHONE_NUMBER",
    "EMAIL": "EMAIL_ADDRESS",
    "NATIONAL_ID": "NATIONAL_ID",  # any country; Presidio's own are per country
    "IBAN": "IBAN_CODE",
    "CARD": "CREDIT_CARD",
    "PASSPORT": "PASSPORT",  # any country
    "ADDRESS": "LOCATION",
    "DATE_OF_BIRTH": "DATE_TIME",
    "IP_ADDRESS": "IP_ADDRESS",
}


class DecimaPIIRecognizer(EntityRecognizer):
    """Wrap a decima-pii model as a Presidio recognizer.

    :param model: A loaded DecimaPII model (can be shared between languages)
    :param supported_language: The Presidio language code this instance serves
    :param score: Score given to every span (the model returns spans, not
    probabilities)
    """

    def __init__(
        self,
        model: DecimaPII,
        supported_language: str = "en",
        entity_mapping: Optional[dict] = None,
        score: float = 0.85,
    ):
        self.model = model
        self.entity_mapping = entity_mapping or DECIMA_TO_PRESIDIO
        self.score = score
        super().__init__(
            supported_entities=sorted(set(self.entity_mapping.values())),
            supported_language=supported_language,
            name="DecimaPIIRecognizer",
        )

    def load(self) -> None:
        pass  # the model is loaded once, outside the recognizer

    def analyze(
        self, text: str, entities: List[str], nlp_artifacts: NlpArtifacts = None
    ) -> List[RecognizerResult]:
        results = []
        for span in self.model.find(text):
            entity = self.entity_mapping.get(span["label"])
            if entity is None or (entities and entity not in entities):
                continue
            explanation = AnalysisExplanation(
                recognizer=self.name,
                original_score=self.score,
                textual_explanation=f"Identified as {span['label']} by decima-pii",
            )
            results.append(
                RecognizerResult(
                    entity_type=entity,
                    start=span["start"],
                    end=span["end"],
                    score=self.score,
                    analysis_explanation=explanation,
                    recognition_metadata={
                        RecognizerResult.RECOGNIZER_NAME_KEY: self.name,
                        RecognizerResult.RECOGNIZER_IDENTIFIER_KEY: self.id,
                    },
                )
            )
        return results


languages = ["ar", "fa", "ur", "tr", "en"]

# Downloads the int8 ONNX model (148 MB) from the Hugging Face Hub on first use
model = DecimaPII.from_pretrained("amyrmahdy/decima-pii", threads=4)

# One recognizer per language, all sharing the same model
registry = RecognizerRegistry(supported_languages=languages)
for language in languages:
    registry.add_recognizer(DecimaPIIRecognizer(model, supported_language=language))

# decima-pii works on raw text, so no spaCy model is needed for these languages
nlp_engine = NoOpNlpEngine(
    models=[{"lang_code": language, "model_name": "no_op"} for language in languages]
)

analyzer = AnalyzerEngine(
    registry=registry, nlp_engine=nlp_engine, supported_languages=languages
)
anonymizer = AnonymizerEngine()

texts = {
    "ar": "اسمي محمود الشمري ورقم جوالي ٠٥٥١٢٣٤٥٦٧ وبريدي m.alshammari@example.com",
    "fa": "سلام، من سارا احمدی هستم. کد ملی من ۰۰۱۲۳۴۵۶۷۸ و شماره موبایلم ۰۹۱۲۳۴۵۶۷۸۹ است.",
}

for language, text in texts.items():
    results = analyzer.analyze(text=text, language=language)
    for result in sorted(results, key=lambda r: r.start):
        print(result.entity_type, "|", text[result.start : result.end], "|", result.score)
    print(anonymizer.anonymize(text=text, analyzer_results=results).text)
    print()
```

Output:

```
PERSON | محمود الشمري | 0.85
PHONE_NUMBER | ٠٥٥١٢٣٤٥٦٧ | 0.85
EMAIL_ADDRESS | m.alshammari@example.com | 0.85
اسمي <PERSON> ورقم جوالي <PHONE_NUMBER> وبريدي <EMAIL_ADDRESS>

PERSON | سارا احمدی | 0.85
NATIONAL_ID | ۰۰۱۲۳۴۵۶۷۸ | 0.85
PHONE_NUMBER | ۰۹۱۲۳۴۵۶۷۸۹ | 0.85
سلام، من <PERSON> هستم. کد ملی من <NATIONAL_ID> و شماره موبایلم <PHONE_NUMBER> است.
```

Urdu and Turkish text are analyzed the same way, with `language="ur"` or `language="tr"`.

## Using it next to Presidio's predefined recognizers

To add decima-pii to an existing English setup, keep the predefined recognizers and remove `SpacyRecognizer`. On Arabic-script text the English spaCy model tends to tag whole phrases as `ORGANIZATION` or `PERSON`, and these longer spans win over decima-pii's spans when the anonymizer resolves overlaps.

This snippet reuses `DecimaPIIRecognizer` and `model` from the example above, and uses the small English spaCy model `en_core_web_sm` (Presidio downloads it if it is not installed).

```python
from presidio_analyzer.nlp_engine import NlpEngineProvider

nlp_engine = NlpEngineProvider(
    nlp_configuration={
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
    }
).create_engine()

analyzer = AnalyzerEngine(nlp_engine=nlp_engine)  # Presidio's predefined recognizers
analyzer.registry.remove_recognizer("SpacyRecognizer")
analyzer.registry.add_recognizer(DecimaPIIRecognizer(model, supported_language="en"))

text = "Sara Ahmadi, کد ملی ۰۰۱۲۳۴۵۶۷۸, card 4111 1111 1111 1111, sara.ahmadi@example.com"
results = analyzer.analyze(text=text, language="en")
for result in sorted(results, key=lambda r: (r.start, -r.score)):
    print(
        result.entity_type, "|", text[result.start : result.end], "|",
        result.recognition_metadata["recognizer_name"],
    )
print(AnonymizerEngine().anonymize(text=text, analyzer_results=results).text)
```

Output:

```
PERSON | Sara Ahmadi | DecimaPIIRecognizer
NATIONAL_ID | ۰۰۱۲۳۴۵۶۷۸ | DecimaPIIRecognizer
CREDIT_CARD | 4111 1111 1111 1111 | CreditCardRecognizer
EMAIL_ADDRESS | sara.ahmadi@example.com | EmailRecognizer
URL | example.com | UrlRecognizer
<PERSON>, کد ملی <NATIONAL_ID>, card <CREDIT_CARD>, <EMAIL_ADDRESS>
```

decima-pii also found the card number and the email here; when two recognizers return the same span and entity, Presidio keeps the higher-scoring result.

## Accuracy and limitations

Numbers reported by the model author, on test sets the model was not trained on:

- [MultiGraSCCo](https://zenodo.org/records/18847836) (clinical letters in English, Arabic, Persian and Turkish; names, phones, emails, addresses and dates of birth): relaxed typed F1 0.870, against 0.647 for `openai/privacy-filter`.
- [Bayanat Labs arabic-pii-eval](https://huggingface.co/datasets/Bayanat-Labs/arabic-pii-eval) (1,000 Arabic test sentences; 38% use Arabic-Indic and 7% Persian digits): exact typed F1 0.953.

See the [model card](https://huggingface.co/amyrmahdy/decima-pii) for the details and per-language results. Limitations:

- Only 5 of the 10 types are measured on outside data. National IDs, IBANs, cards, passports and IP addresses are measured only on the author's synthetic test set. Urdu has no outside test yet.
- It is a PII detector, not a complete de-identification tool: it does not tag organizations, general dates, ages, record numbers or job titles. Use it as one layer and review the output.
- Every span gets the same score (`score` in the recognizer above), so score thresholds do not rank decima-pii's results.
