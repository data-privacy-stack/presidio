# The Presidio-analyzer decision process

## Background

Presidio-analyzer's decision process exposes information on why a specific PII was detected. Such information could contain:

- Which recognizer detected the entity
- Which regex pattern was used
- Interpretability mechanisms in ML models
- Which context words improved the score
- Confidence scores before and after each step

And more.

## Usage

The decision process can be leveraged in two ways:

1. Presidio-analyzer can log its decision process into a designated logger, which allows you to investigate a specific api request, by exposing a `correlation-id` as part of the api response headers.
2. The decision process can be returned as part of the `/analyze`  response.

### Getting the decision process as part of the response

The decision process result can be added to the response.
To enable it, call the `analyze` method with `return_decision_process` set as True.

For example:

=== "HTTP"

    ```sh
    curl -d '{
        "text": "John Smith drivers license is AC432223", 
        "language": "en", 
        "return_decision_process": true}' -H "Content-Type: application/json" -X POST http://localhost:3000/analyze
    ```

=== "Python"

    ```python
    from presidio_analyzer import AnalyzerEngine

    # Set up the engine, loads the NLP module (spaCy model by default)
    # and other PII recognizers
    analyzer = AnalyzerEngine()

    # Call analyzer to get results
    results = analyzer.analyze(text='My phone number is 212-555-5555', 
                            entities=['PHONE_NUMBER'], 
                            language='en', 
                            return_decision_process=True)
    
    # Get the decision process results for the first result
    print(results[0].analysis_explanation)
    ```

### Logging the decision process

Logging of the decision process is turned off by default. To turn it on, create the `AnalyzerEngine` object with `log_decision_process=True`.

For example:

```python
from presidio_analyzer import AnalyzerEngine

# Set up the engine, loads the NLP module (spaCy model by default)
# and other PII recognizers
analyzer = AnalyzerEngine(log_decision_process=True)

# Call analyzer to get results
results = analyzer.analyze(text='My phone number is 212-555-5555', 
                           entities=['PHONE_NUMBER'], 
                           language='en', 
                           correlation_id="xyz")
```

The decision process logs will be written to standard output.
Note that it is possible to define a `correlation-id` which is the trace identification. It will help you to query the stdout logs.
The id can be retrieved from each API response header: `x-correlation-id`.

By having the traces written into the `stdout` it's very easy to configure a monitoring solution to ease the process of reading processing the tracing logs in a distributed system.

## Examples

For the a request with the following text:

```text
My name is Bart Simpson, my Credit card is: 4095-2609-9393-4932,  my phone is 425 8829090 
```

The following traces will be written to log, with this format:

`[Date Time][decision_process][Log Level][Unique Correlation ID][Trace Message]`

```text
[2019-07-14 14:22:32,409][decision_process][INFO][00000000-0000-0000-0000-000000000000][nlp artifacts:{'entities': (Bart Simpson, 4095, 425), 'tokens': ['My', 'name', 'is', 'Bart', 'Simpson', ',', 'my', 'Credit', 'card', 'is', ':', '4095', '-', '2609', '-', '9393', '-', '4932', ',', ' ', 'my', 'phone', 'is', '425', '8829090'], 'lemmas': ['My', 'name', 'be', 'Bart', 'Simpson', ',', 'my', 'Credit', 'card', 'be', ':', '4095', '-', '2609', '-', '9393', '-', '4932', ',', ' ', 'my', 'phone', 'be', '425', '8829090'], 'tokens_indices': [0, 3, 8, 11, 16, 23, 25, 28, 35, 40, 42, 44, 48, 49, 53, 54, 58, 59, 63, 65, 66, 69, 75, 78, 82], 'keywords': ['bart', 'simpson', 'credit', 'card', '4095', '2609', '9393', '4932', ' ', 'phone', '425', '8829090']}]

[2019-07-14 14:22:32,417][decision_process][INFO][00000000-0000-0000-0000-000000000000][["{'entity_type': 'CREDIT_CARD', 'start': 44, 'end': 63, 'score': 1.0, 'analysis_explanation': {'recognizer': 'CreditCardRecognizer', 'pattern_name': 'All Credit Cards (weak)', 'pattern': '\\\\b((4\\\\d{3})|(5[0-5]\\\\d{2})|(6\\\\d{3})|(1\\\\d{3})|(3\\\\d{3}))[- ]?(\\\\d{3,4})[- ]?(\\\\d{3,4})[- ]?(\\\\d{3,5})\\\\b', 'original_score': 0.3, 'score': 1.0, 'textual_explanation': None, 'score_context_improvement': 0.7, 'supportive_context_word': 'credit', 'validation_result': True}}", "{'entity_type': 'PERSON', 'start': 11, 'end': 23, 'score': 0.85, 'analysis_explanation': {'recognizer': 'SpacyRecognizer', 'pattern_name': None, 'pattern': None, 'original_score': 0.85, 'score': 0.85, 'textual_explanation': \"Identified as PERSON by Spacy's Named Entity Recognition\", 'score_context_improvement': 0, 'supportive_context_word': '', 'validation_result': None}}", "{'entity_type': 'PHONE_NUMBER', 'start': 78, 'end': 89, 'score': 0.85, 'analysis_explanation': {'recognizer': 'UsPhoneRecognizer', 'pattern_name': 'Phone (medium)', 'pattern': '\\\\b(\\\\d{3}[-\\\\.\\\\s]\\\\d{3}[-\\\\.\\\\s]??\\\\d{4})\\\\b', 'original_score': 0.5, 'score': 0.85, 'textual_explanation': None, 'score_context_improvement': 0.35, 'supportive_context_word': 'phone', 'validation_result': None}}"]]
```

## Writing custom decision process for a recognizer

When creating new PII recognizers, it is possible to add information about the recognizer's decision process. This information will be traced or returned to the user, depending on the configuration.

For example, the [spacy_recognizer.py](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/nlp_engine_recognizers/spacy_recognizer.py) implements a custom trace as follows:

```python
SPACY_DEFAULT_EXPLANATION = "Identified as {} by Spacy's Named Entity Recognition"

def build_spacy_explanation(recognizer_name, original_score, entity):
    explanation = AnalysisExplanation(
        recognizer=recognizer_name,
        original_score=original_score,
        textual_explanation=SPACY_DEFAULT_EXPLANATION.format(entity))
    return explanation
```

The `textual_explanation` field in `AnalysisExplanation` class allows you to add your own custom text into the final trace which will be written.

!!! note "Note"
    These traces leverage the Python `logging` mechanisms. In the default configuration, A `StreamHandler` is used to write these logs to `sys.stdout`.

!!! warning "Warning"
    Decision-process traces explain why PIIs were detected,
    but not why they were not detected!
