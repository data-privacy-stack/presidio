# Azure AI Language Integration

## Introduction

Azure Text Analytics is a cloud-based service that provides advanced natural
language processing over raw text. One of its main functions includes 
Named Entity Recognition (NER), which has the ability to identify different
entities in text and categorize them into pre-defined classes or types.
This document will demonstrate Presidio integration with Azure Text Analytics.

## Supported entity categories in the Text Analytics API
Azure AI Language supports multiple PII entity categories. The Azure AI Laguage service
runs a predictive model to identify and categorize named entities from an input
document. The service's latest version includes the ability to detect personal (PII)
and health (PHI) information. A list of all supported entities can be found in the
[official documentation](https://docs.microsoft.com/en-us/azure/cognitive-services/text-analytics/named-entity-types?tabs=personal).

## Prerequisites
To use Azure AI Language with Preisido, an Azure AI Language resource should
first be created under an Azure subscription. Follow the [official documentation](https://docs.microsoft.com/en-us/azure/cognitive-services/text-analytics/how-tos/text-analytics-how-to-call-api?tabs=synchronous#create-a-text-analytics-resource)
for instructions. The key and endpoint, generated once the resource is created, 
will be used when integrating with Text Analytics, using a Presidio Text Analytics recognizer.

## Azure AI Language Recognizer
[The implementation of a `AzureAILanguage` recognizer can be found here](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/third_party/azure_ai_language.py).

## How to integrate Azure AI Language into Presidio

1. Install the package with the azure-ai-language extra:
  ```sh
  pip install "presidio-analyzer[azure-ai-language]"
  ```

2. Define environment varibles `AZURE_AI_KEY` and `AZURE_AI_ENDPOINT`

3. Add the `AzureAILanguageRecognizer` to the recognizer registry:
  
  ```python
  from presidio_analyzer import AnalyzerEngine
  from presidio_analyzer.predefined_recognizers import AzureAILanguageRecognizer
    
  azure_ai_language = AzureAILanguageRecognizer()
  
  analyzer = AnalyzerEngine()
  analyzer.registry.add_recognizer(azure_ai_language)
  
  analyzer.analyze(text="My email is email@email.com", language="en")
  ```
