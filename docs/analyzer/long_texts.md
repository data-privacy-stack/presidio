# Analyzing long texts

The memory and the time that Presidio Analyzer needs grow with the length of the text.
The NLP engine processes the whole text in one pass before the recognizers run.
For example, spaCy estimates that its parser and NER models need roughly 1GB of temporary memory per 100,000 characters.
A very long text can therefore need more memory than the deployment has.

Presidio does not split a text on its own.
To analyze a long text, split it before calling `analyze`.

## Split the text before calling `analyze`

The `CharacterBasedTextChunker` splits a text at spaces and line breaks.
Its `predict_with_chunking` method runs a function on each chunk, moves the results to their positions in the full text, and removes the duplicates that come from the overlap between chunks:

```python
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.chunkers import CharacterBasedTextChunker

analyzer = AnalyzerEngine()
chunker = CharacterBasedTextChunker(chunk_size=5000, chunk_overlap=200)

long_text = "My name is David Johnson and my phone number is 212-555-0198. " * 500

results = chunker.predict_with_chunking(
    long_text,
    lambda chunk: analyzer.analyze(text=chunk, language="en"),
)
```

The results have the same form as the results of one `analyze` call on the full text, so they can be passed to the Presidio Anonymizer together with the full text.

Things to consider:

- **Chunk size.** No single size is right for all deployments. A safe size depends on the NLP model and on the memory that is available. Measure it with your own model and texts.
- **Entities at a chunk edge.** An entity that is cut by a chunk edge can be missed or detected only in part. Use an overlap that is longer than the longest entity you expect. Even then, results close to a chunk edge can differ from the results on the full text.
- **Context words.** A context word raises the score of a match only if both are in the same chunk.
- **Texts without spaces or line breaks.** The chunker does not split such a text, so it is analyzed as one chunk.
- **Speed.** The chunks are analyzed one after the other.

## Reject texts that are too long

A deployment can also refuse a text that is too long, so that one request cannot use all the memory.
With the spaCy NLP engine, set `max_length` for the model. See [Limit the text length](nlp_engines/spacy_stanza.md#limit-the-text-length-spacy).
A longer text then raises an error before any processing, and the REST API returns status `413`.
No part of the text is analyzed, so the caller has to split the text and send it again.

## Skip the NLP model if it is not needed

If all your recognizers are pattern-based, the NLP model is not needed to detect entities.
See [Running without an NLP model](customizing_nlp_models.md#running-without-an-nlp-model) for this setup and for its effect on scores.

## Recognizers that run their own model

`GLiNERRecognizer` and `HuggingFaceNerRecognizer` split a long text on their own before they call their model.
See the `text_chunker` parameter in [Recognizer registry from file](recognizer_registry_provider.md).
This does not change how the NLP engine processes the text.
