# Azure Health Data Services de-identification Integration

## Introduction

The Azure Health Data Services (AHDS) de-identification Service is a cloud-based 
service that provides advanced natural language processing over 
raw text. One of its main functions includes Named Entity Recognition 
(NER), which has the ability to identify different
entities in text and categorize them into pre-defined classes or types.
This document will demonstrate Presidio integration with the AHDS
De-Identification Service.

## Supported entity categories in the Azure Health Data Services de-identification API
Azure Health Data Services de-identification supports multiple PII entity categories.
The Azure Health Data Services de-identification service
runs a predictive model to identify and categorize named entities from an input
document. The service's latest version includes the ability to detect personal (PII)
and health (PHI) information. A list of all supported entities can be found in the
[official documentation](https://learn.microsoft.com/en-us/azure/healthcare-apis/deidentification/overview).

## Prerequisites
To use AHDS De-Identification with Presidio, an Azure De-Identification Service resource should
first be created under an Azure subscription. Follow the [official documentation](https://learn.microsoft.com/en-us/azure/healthcare-apis/deidentification/quickstart)
for instructions. The endpoint, generated once the resource is created, 
will be used when integrating with AHDS De-Identification, using a Presidio remote recognizer.

### Authentication Setup

The integration uses a secure-by-default authentication approach:

**Production Mode (Default)**: Uses a restricted credential chain (EnvironmentCredential, WorkloadIdentityCredential, ManagedIdentityCredential)

**Development Mode**: Set `ENV=development` to use DefaultAzureCredential for local development with Azure CLI:
```bash
export ENV=development
az login
```

For more details, see the [AHDS Integration Authentication documentation](../../../ahds_integration.md#authentication).

## Azure Health Data Services de-identification Recognizer
[The implementation of a `AzureHealthDeid` recognizer can be found here](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/predefined_recognizers/third_party/ahds_recognizer.py).

## How to integrate Azure Health Data Services de-identification into Presidio

1. Install the package with the ahds extra:
  ```sh
  pip install "presidio-analyzer[ahds]"
  ```

2. Define environment variables `AHDS_ENDPOINT`

3. Add the `AzureHealthDeidRecognizer` to the recognizer registry:
  
  ```python
  from presidio_analyzer import AnalyzerEngine
  from presidio_analyzer.predefined_recognizers import AzureHealthDeidRecognizer
    
  ahds = AzureHealthDeidRecognizer()
  
  analyzer = AnalyzerEngine()
  analyzer.registry.add_recognizer(ahds)
  
  analyzer.analyze(text="My email is email@email.com", language="en")
  ```

---
**See also:**
For a full surrogate integration example, see [example_ahds_surrogate.py](example_ahds_surrogate.py)
