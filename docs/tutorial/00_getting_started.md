# Getting started

## Installation

First, let's install presidio using `pip`. For detailed documentation, see the [installation docs](https://data-privacy-stack.github.io/presidio/installation).
Install from PyPI:

```sh
pip install presidio_analyzer
pip install presidio_anonymizer
python -m spacy download en_core_web_lg
```

## Simple flow

A simple call to Presidio Analyzer:
<!--pytest-codeblocks:cont-->
```python
from presidio_analyzer import AnalyzerEngine

text = "His name is Mr. Jones and his phone number is 212-555-5555"

analyzer = AnalyzerEngine()
analyzer_results = analyzer.analyze(text=text, language="en")

print(analyzer_results)
```

Next, we'll go over ways to customize Presidio to specific needs by adding PII recognizers, using context words, NER models and more.
