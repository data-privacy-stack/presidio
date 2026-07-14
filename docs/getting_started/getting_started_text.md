# Getting started with text de-identification with Presidio

Presidio provides a simple way to de-identify text data by detecting and anonymizing personally identifiable information (PII). This guide shows you how to get started with text de-identification using Presidio's Python packages.

Note that Presidio can leverage different NLP packages to analyze text data. The default engine is based on `spaCy`, but you can [also use others](../analyzer/customizing_nlp_models.md). This guide shows two examples: one using `spaCy` and the other using `transformers`.

## Simple flow - Python package

Using Presidio's modules as Python packages to get started:

===+ "Anonymize PII in text (Default spaCy model)"

    1. Install Presidio
        
        ```sh
        pip install presidio-analyzer
        pip install presidio-anonymizer
        python -m spacy download en_core_web_lg
        ```
    
    2. Analyze + Anonymize
    
        ```py
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine
        
        text="My phone number is 212-555-5555"
        
        # Set up the engine, loads the NLP module (spaCy model by default) 
        # and other PII recognizers
        analyzer = AnalyzerEngine()
        
        # Call analyzer to get results
        results = analyzer.analyze(text=text,
                                   entities=["PHONE_NUMBER"],
                                   language='en')
        print(results)
        
        # Analyzer results are passed to the AnonymizerEngine for anonymization
        
        anonymizer = AnonymizerEngine()
        
        anonymized_text = anonymizer.anonymize(text=text,analyzer_results=results)
        
        print(anonymized_text)
        ```

=== "Anonymize PII in text (transformers)"

    1. Install Presidio
        
        ```sh
        pip install "presidio-analyzer[transformers]"
        pip install presidio-anonymizer
        python -m spacy download en_core_web_sm
        ```
    
    2. Analyze + Anonymize
    
        ```py
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import TransformersNlpEngine
        from presidio_anonymizer import AnonymizerEngine
        
        text = "My name is Don and my phone number is 212-555-5555"
        
        # Define which transformers model to use
        model_config = [{"lang_code": "en", "model_name": {
            "spacy": "en_core_web_sm",  # use a small spaCy model for lemmas, tokens etc.
            "transformers": "dslim/bert-base-NER"
            }
        }]

        nlp_engine = TransformersNlpEngine(models=model_config)

        # Set up the engine, loads the NLP module (spaCy model by default) 
        # and other PII recognizers
        analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
        
        # Call analyzer to get results
        results = analyzer.analyze(text=text, language='en')
        print(results)
        
        # Analyzer results are passed to the AnonymizerEngine for anonymization
        
        anonymizer = AnonymizerEngine()
        
        anonymized_text = anonymizer.anonymize(text=text, analyzer_results=results)
        
        print(anonymized_text)
        
        ```
        !!! tip "Tip: Downloading models"
            If not available, the transformers model and the spacy model would be downloaded on the first call to the `AnalyzerEngine`. To pre-download, see [this doc](../analyzer/nlp_engines/transformers.md#downloading-a-pre-trained-model).

=== "GPU Acceleration (Optional)"

    For GPU acceleration, install the appropriate dependencies for your hardware:

    - **Linux with NVIDIA GPU**: cupy-cuda12x (or the version matching your CUDA installation)
    - **macOS with Apple Silicon**: MPS (Metal Performance Shaders) is currently not supported. The analyzer will use CPU for PyTorch operations.

## Simple flow - Docker container

Presidio provides Docker containers that you can use to de-identify text data. Each module, analyzer, and anonymizer, has its own Docker container. New releases are available on [GitHub Container Registry](https://github.com/orgs/data-privacy-stack/packages); the legacy Microsoft Container Registry images are no longer updated.

1. Download Docker images

```sh
docker pull ghcr.io/data-privacy-stack/presidio-analyzer
docker pull ghcr.io/data-privacy-stack/presidio-anonymizer
```

2. Run containers

```sh
docker run -d -p 5002:3000 ghcr.io/data-privacy-stack/presidio-analyzer:latest

docker run -d -p 5001:3000 ghcr.io/data-privacy-stack/presidio-anonymizer:latest
```

3. Use the API

```sh
curl -X POST http://localhost:5002/analyze \
-H "Content-Type: application/json" \
-d '{
  "text": "My phone number is 555-123-4567.",
  "language": "en"
}'


curl -X POST http://localhost:5001/anonymize -H "Content-Type: application/json"  -d '
    {
        "text": "My phone number is 555-123-4567",
        "anonymizers": {
            "PHONE_NUMBER": {
            "type": "replace",
            "new_value": "--Redacted phone number--"
            }
        },
        "analyzer_results": [
        {
            "start": 19,
            "end": 31,
            "score": 0.95,
            "entity_type": "PHONE_NUMBER"
        }
    ]}'

```

## Read more

- [Installing Presidio](../installation.md)
- [PII detection in text](../analyzer/index.md)
- [PII anonymization in text](../anonymizer/index.md)
- [Tutorial](../tutorial/index.md)
- [Samples](../samples/index.md)
- [Python API reference - Analyzer](../api/analyzer_python.md)
- [Python API reference - Anonymizer](../api/anonymizer_python.md)
- [REST API reference](../api-docs/api-docs.html)
