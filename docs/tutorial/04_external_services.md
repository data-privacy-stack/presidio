# Example 4: Calling an external service/framework for PII detection

In a similar way to example 3, we can write logic to call external services for PII detection. There are two types of external services we support:

1. Remote services such as a PII detection model hosted somewhere. In this case, the recognizer would do the actual REST request and translate the results to a list of `RecognizerResult`.
2. Calling PII models from other frameworks, such as [transformers](https://huggingface.co/transformers/usage.html#named-entity-recognition) or [Flair](https://github.com/flairNLP/flair).

## Calling a remote service

1. [Documentation on remote recognizers](https://data-privacy-stack.github.io/presidio/analyzer/adding_recognizers/#creating-a-remote-recognizer).

2. [A sample implementation of a remote recognizer](https://github.com/data-privacy-stack/presidio/blob/main/docs/samples/python/example_remote_recognizer.py).

## Calling a model in a different framework

- [This example](https://github.com/data-privacy-stack/presidio/blob/main/docs/samples/python/flair_recognizer.py) shows a Presidio wrapper for a Flair model.
- Using a similar approach, we could create wrappers for HuggingFace models, Conditional Random Fields or any other framework.
