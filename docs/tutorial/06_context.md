# Example 6: Leveraging context words

Presidio has an internal mechanism for leveraging context words. This mechanism would increase the detection confidence of a PII entity in case a specific word appears before or after it.

Furthermore, it is possible to create your own context enhancer, if you require a different logic for identifying context terms. The default context-aware enhancer in Presidio is the `LemmaContextAwareEnhancer` which compares each recognizer's context terms with the lemma of each token in the sentence.

In this example we would first implement a zip code recognizer without context, and then add context to see how the confidence changes. Zip regex patterns (essentially 5 digits) are very weak, so we would want the initial confidence to be low, and increased with the existence of context words.

## Example: Adding context words support to recognizers

First, let's create a simple `US_ZIP_CODE` recognizer:

<!--pytest-codeblocks:cont-->
```python
from presidio_analyzer import (
    Pattern,
    PatternRecognizer,
    RecognizerRegistry,
    AnalyzerEngine,
)

# Define the regex pattern
regex = r"(\b\d{5}(?:\-\d{4})?\b)"  # very weak regex pattern
zipcode_pattern = Pattern(name="zip code (weak)", regex=regex, score=0.01)

# Define the recognizer with the defined pattern
zipcode_recognizer = PatternRecognizer(
    supported_entity="US_ZIP_CODE", patterns=[zipcode_pattern]
)

registry = RecognizerRegistry()
registry.add_recognizer(zipcode_recognizer)
analyzer = AnalyzerEngine(registry=registry)

# Test
results = analyzer.analyze(text="My zip code is 90210", language="en")

print(f"Result:\n {results}")
```

So this is working, but would catch any 5 digit string. This is why we set the score to 0.01. Let's use context words to increase score:

<!--pytest-codeblocks:cont-->
```python
from presidio_analyzer import PatternRecognizer

# Define the recognizer with the defined pattern and context words
zipcode_recognizer_w_context = PatternRecognizer(
    supported_entity="US_ZIP_CODE",
    patterns=[zipcode_pattern],
    context=["zip", "zipcode"],
)
```

When creating an ```AnalyzerEngine``` we can provide our own context enhancement logic by passing it to ```context_aware_enhancer``` parameter.
```AnalyzerEngine``` will create ```LemmaContextAwareEnhancer``` by default if not passed, which will enhance score of each matched result if its recognizer holds context words and the lemma of those words are found in the surroundings of the matched entity.

Creating the `AnalyzerEngine` and adding the new recognizer:

<!--pytest-codeblocks:cont-->
```python
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry

registry = RecognizerRegistry()
registry.add_recognizer(zipcode_recognizer_w_context)
analyzer = AnalyzerEngine(registry=registry)

# Test
results = analyzer.analyze(text="My zip code is 90210", language="en")
print("Result:")
print(results)
```

The confidence score is now 0.4, instead of 0.01, since the ```LemmaContextAwareEnhancer``` default context similarity factor is 0.35 and default minimum score with context similarity is 0.4. We can change that by passing other values to the ```context_similarity_factor``` and ```min_score_with_context_similarity``` parameters of the ```LemmaContextAwareEnhancer``` object. For example:

<!--pytest-codeblocks:cont-->
```python
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer

context_aware_enhancer = LemmaContextAwareEnhancer(
    context_similarity_factor=0.45, min_score_with_context_similarity=0.4
)

registry = RecognizerRegistry()
registry.add_recognizer(zipcode_recognizer_w_context)
analyzer = AnalyzerEngine(
    registry=registry, context_aware_enhancer=context_aware_enhancer
)

# Test
results = analyzer.analyze(text="My zip code is 90210", language="en")
print("Result:")
print(results)
```

The confidence score is now 0.46 because it got enhanced from 0.01 with 0.45 and is more than the minimum of 0.4.

In addition to surrounding words, additional context words could be passed on the request level.
This is useful when there is context coming from metadata such as column names or a specific user input.
In the following example, notice how the "zip" context word doesn't appear in the text but still enhances the confidence score from 0.01 to 0.4:

<!--pytest-codeblocks:cont-->
```python
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, PatternRecognizer

# Define the recognizer with the defined pattern and context words
zipcode_recognizer = PatternRecognizer(
    supported_entity="US_ZIP_CODE",
    patterns=[zipcode_pattern],
    context=["zip", "zipcode"],
)
registry = RecognizerRegistry()
registry.add_recognizer(zipcode_recognizer)
analyzer = AnalyzerEngine(registry=registry)

# Test with an example record having a column name which could be injected as context
record = {"column_name": "zip", "text": "My code is 90210"}

result = analyzer.analyze(
    text=record["text"], language="en", context=[record["column_name"]]
)

print("Result:")
print(result)
```

## Example: Reducing confidence with negative context words

While positive context words increase confidence in PII detection, Presidio also supports negative context words that *reduce* confidence when found near a detected entity. This is useful for filtering out false positives from test data, examples, or documentation.

Common use cases include:
- Filtering test data (e.g., "test SSN", "example email")
- Avoiding sample/mock data (e.g., "sample username", "mock password")
- Ignoring documentation (e.g., "For example: john@example.com")

Let's create a US Social Security Number recognizer without negative context first:

<!--pytest-codeblocks:cont-->
```python
from presidio_analyzer import (
    Pattern,
    PatternRecognizer,
    RecognizerRegistry,
    AnalyzerEngine,
)

# Define the regex pattern
regex = r"(\d{3}-\d{2}-\d{4})"
ssn_pattern = Pattern(name="ssn (weak)", regex=regex, score=0.9)

# Define the recognizer WITHOUT negative context
ssn_recognizer = PatternRecognizer(
    supported_entity="US_SSN", patterns=[ssn_pattern]
)

registry = RecognizerRegistry()
registry.add_recognizer(ssn_recognizer)
analyzer = AnalyzerEngine(registry=registry)

# Test
text = "This is a test SSN: 123-45-6789"
results = analyzer.analyze(text=text, language="en")
print(f"Result:\n {results}")
print(f"Score: {results[0].score if results else 'N/A'}")
```

The score is high (0.9) even though the text clearly indicates this is test data. Let's add negative context words to filter this out:

<!--pytest-codeblocks:cont-->
```python
from presidio_analyzer import PatternRecognizer

# Define the recognizer WITH negative context
ssn_recognizer_w_negative_context = PatternRecognizer(
    supported_entity="US_SSN",
    patterns=[ssn_pattern],
    negative_context=["test", "example", "dummy"],
)
```

Now let's test with the updated recognizer:

<!--pytest-codeblocks:cont-->
```python
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry

registry = RecognizerRegistry()
registry.add_recognizer(ssn_recognizer_w_negative_context)
analyzer = AnalyzerEngine(registry=registry)

# Test with negative context word in text
text = "This is a test SSN: 123-45-6789"
results = analyzer.analyze(text=text, language="en")
print(f"Result:\n {results}")
if results:
    print(f"Score: {results[0].score}")
else:
    print("Entity filtered out by negative context!")
```

The score is now reduced from 0.9 to approximately 0.6 (base score 0.9 minus default penalty of 0.3), which is typically below the confidence threshold and gets filtered out.

### How negative context scoring works

The negative context penalty is applied during the enhancement phase:

```
final_score = max(base_score - negative_context_penalty, 0)
```

- **base_score**: The original detection score (e.g., 0.9)
- **negative_context_penalty**: Default is 0.3 (can be configured)
- **final_score**: Never goes below 0

### Comparison table

| Text | Base Score | Negative Context Found | Final Score | Detection |
|------|-----------|----------------------|-------------|-----------|
| "My SSN is 123-45-6789" | 0.9 | No | 0.9 |  Detected |
| "Test SSN: 123-45-6789" | 0.9 | Yes ("test") | 0.6 |  Filtered |
| "Example: 123-45-6789" | 0.9 | Yes ("example") | 0.6 | Filtered |
| "SSN 555-55-5555" | 0.9 | No | 0.9 |  Detected |

### Configuration methods for negative context

Negative context can be configured in three ways:

**Method 1: Recognizer-level (static)**

Define negative context words when creating the recognizer:

<!--pytest-codeblocks:cont-->
```python
recognizer = PatternRecognizer(
    supported_entity="US_SSN",
    patterns=[ssn_pattern],
    negative_context=["test", "example", "dummy"],
)
```

**Method 2: Runtime (dynamic)**

Pass negative context words at the request level:

<!--pytest-codeblocks:cont-->
```python
results = analyzer.analyze(
    text="This is a sample SSN: 123-45-6789",
    language="en",
    negative_context=["sample", "mock"],
)
```

**Method 3: Enhancer tuning**

Adjust the penalty factor applied to all negative context matches:

<!--pytest-codeblocks:cont-->
```python
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer

# Increase penalty to 0.5 instead of default 0.3
enhancer = LemmaContextAwareEnhancer(negative_context_penalty=0.5)

registry = RecognizerRegistry()
registry.add_recognizer(ssn_recognizer_w_negative_context)
analyzer = AnalyzerEngine(
    registry=registry, context_aware_enhancer=enhancer
)

results = analyzer.analyze(text="This is a test SSN: 123-45-6789", language="en")
print(f"Score with higher penalty: {results[0].score if results else 'Filtered'}")
```

### Important notes

- **Backward compatibility**: Negative context is optional. If not specified, it defaults to an empty list and has no effect.
- **Explicit disabling**: Passing an empty list `[]` explicitly disables negative context, even if a recognizer has default negative context configured.
- **Independent of positive context**: Negative context is evaluated separately from positive context. Both can be active simultaneously.
- **Combining with positive context**: If both positive and negative context words are present in the text, both effects are applied to the score.
