# Example 2: Regular-expressions based PII recognition

Another simple recognizer we can add is based on regular expressions.
Let's assume we want to be extremely conservative and treat any token which contains a number as PII.

<!--pytest-codeblocks:cont-->
```python
from presidio_analyzer import Pattern, PatternRecognizer

# Define the regex pattern in a Presidio `Pattern` object:
numbers_pattern = Pattern(name="numbers_pattern", regex=r"\d+", score=0.5)

# Define the recognizer with one or more patterns
number_recognizer = PatternRecognizer(
    supported_entity="NUMBER", patterns=[numbers_pattern]
)
```

Testing the recognizer itself:

<!--pytest-codeblocks:cont-->
```python
text2 = "I live in 510 Broad st."

numbers_result = number_recognizer.analyze(text=text2, entities=["NUMBER"])

print("Result:")
print(numbers_result)
```

It's important to mention that recognizers are likely to have errors, both false-positive and false-negative, which would impact the entire performance of Presidio. Consider testing each recognizer on a representative dataset prior to integrating it into Presidio. For more info, see the [best practices for developing recognizers documentation](https://data-privacy-stack.github.io/presidio/analyzer/developing_recognizers/).
