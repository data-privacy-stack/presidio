# Example 3: Rule based logic recognizer

Taking the numbers recognizer one step further, let's say we also would like to detect numbers within words, e.g. "Number One". We can leverage the underlying `spaCy` token attributes, or write our own logic to detect such entities.

Notes:

- In this example we would create a new class, which implements [`EntityRecognizer`](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/entity_recognizer.py), the basic recognizer in Presidio. This abstract class requires us to implement the `load` method and `analyze` method.

- Each recognizer accepts an object of type `NlpArtifacts`, which holds pre-computed attributes on the input text.

A new recognizer should have this structure:

<!--pytest-codeblocks:cont-->
```python
from typing import List
from presidio_analyzer import EntityRecognizer, RecognizerResult
from presidio_analyzer.nlp_engine import NlpArtifacts


class MyRecognizer(EntityRecognizer):
    def load(self) -> None:
        """No loading is required."""
        pass

    def analyze(
        self, text: str, entities: List[str], nlp_artifacts: NlpArtifacts
    ) -> List[RecognizerResult]:
        """
        Logic for detecting a specific PII
        """
        pass
```

For example, detecting numbers in either numerical or alphabetic (e.g. Forty five) form:

<!--pytest-codeblocks:cont-->
```python
from typing import List
from presidio_analyzer import EntityRecognizer, RecognizerResult
from presidio_analyzer.nlp_engine import NlpArtifacts


class NumbersRecognizer(EntityRecognizer):

    expected_confidence_level = 0.7  # expected confidence level for this recognizer

    def load(self) -> None:
        """No loading is required."""
        pass

    def analyze(
        self, text: str, entities: List[str], nlp_artifacts: NlpArtifacts
    ) -> List[RecognizerResult]:
        """
        Analyzes test to find tokens which represent numbers (either 123 or One Two Three).
        """
        results = []

        # iterate over the spaCy tokens, and call `token.like_num`
        for token in nlp_artifacts.tokens:
            if token.like_num:
                result = RecognizerResult(
                    entity_type="NUMBER",
                    start=token.idx,
                    end=token.idx + len(token),
                    score=self.expected_confidence_level,
                )
                results.append(result)
        return results


# Instantiate the new NumbersRecognizer:
new_numbers_recognizer = NumbersRecognizer(supported_entities=["NUMBER"])
```

Since this recognizer requires the `NlpArtifacts`, we would have to call it as part of the `AnalyzerEngine` flow:

<!--pytest-codeblocks:cont-->
```python
from presidio_analyzer import AnalyzerEngine

text3 = "Roberto lives in Five 10 Broad st."
analyzer = AnalyzerEngine()
analyzer.registry.add_recognizer(new_numbers_recognizer)

numbers_results2 = analyzer.analyze(text=text3, language="en")
print("Results:")
print("\n".join([str(res) for res in numbers_results2]))
```

The analyzer was able to pick up both numeric and alphabetical numbers, including other types of PII entities from other recognizers (PERSON in this case).
