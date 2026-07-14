# Frequently Asked Questions (FAQ)

- [General](#general)
  - [What is Presidio?](#what-is-presidio)
  - [Why was Presidio created?](#why-was-presidio-created)
  - [Who owns and maintains Presidio?](#who-owns-and-maintains-presidio)
  - [What is the difference between Presidio and different PII detection services like Azure AI Language, Azure Health Data Services, and Amazon Comprehend?](#what-is-the-difference-between-presidio-and-different-pii-detection-services-like-azure-ai-language-and-amazon-comprehend)
- [Using Presidio](#using-presidio)
  - [How can I start using Presidio?](#how-can-i-start-using-presidio)
  - [What are the main building blocks in Presidio?](#what-are-the-main-building-blocks-in-presidio)
- [Customizing Presidio](#customizing-presidio)
  - [How can Presidio be customized to my needs?](#how-can-presidio-be-customized-to-my-needs)
  - [What NLP frameworks does Presidio support?](#what-nlp-frameworks-does-presidio-support)
  - [Can Presidio be used for Pseudonymization?](#can-presidio-be-used-for-pseudonymization)
  - [Does Presidio work on structured/tabular data?](#does-presidio-work-on-structuredtabular-data)
- [Improving detection accuracy](#improving-detection-accuracy)
  - [What can I do if Presidio does not detect some of the PII entities in my data (False Negatives)?](#what-can-i-do-if-presidio-does-not-detect-some-of-the-pii-entities-in-my-data-false-negatives)
  - [What can I do if Presidio falsely detects text as PII entities (False Positives)?](#what-can-i-do-if-presidio-falsely-detects-text-as-pii-entities-false-positives)
  - [How can I evaluate the performance of my Presidio instance?](#how-can-i-evaluate-the-performance-of-my-presidio-instance)
- [Deployment](#deployment)
  - [How can I deploy Presidio into my environment?](#how-can-i-deploy-presidio-into-my-environment)
- [Contributing](#contributing)
  - [How can I contribute to Presidio?](#how-can-i-contribute-to-presidio)
  - [How can I report security vulnerabilities?](#how-can-i-report-security-vulnerabilities)

## General

### What is Presidio?

Presidio (Origin from Latin praesidium ‘protection, garrison’) helps to ensure sensitive data is properly managed and governed. It provides fast identification and anonymization modules for private entities in text and images. It is fully customizable and pluggable, can be adapted to your needs and be deployed into various environments.

!!! note "Note"
    Presidio is a library or SDK rather than a service. It is meant to be customized to the user's or organization's specific needs.

!!! warning "Warning"
    Presidio can help identify sensitive/PII data in un/structured text. However, because it is using automated detection mechanisms, there is no guarantee that Presidio will find all sensitive information. Consequently, additional systems and protections should be employed.

### Why was Presidio created?

By developing Presidio, our goals are:

1. Allow organizations to preserve privacy in a simpler way by democratizing de-identification technologies and introducing transparency in decisions.
2. Embrace extensibility and customizability to a specific business need.
3. Facilitate both fully automated and semi-automated PII de-identification flows on multiple platforms.

### Who owns and maintains Presidio?

Presidio is a community-governed open source project under the [Data Privacy Stack](https://github.com/data-privacy-stack) organization. It was originally created at Microsoft and has since transitioned to an independent, vendor-neutral project maintained by contributors and volunteers from across the community. See the [project transition update](project_transition.md) for more details.

!!! note "Note"
    Presidio is not an official product of any company and comes with no warranty or SLA. Usage terms are defined in the [repository's license](https://github.com/data-privacy-stack/presidio/blob/main/LICENSE).

### What is the difference between Presidio and different PII detection services like Azure AI Language, Azure Health Data Services, and Amazon Comprehend?

In a nutshell, Presidio is a library which is meant to be customized, whereas different SaaS tools for PII detection have less customization capabilities. Most of these SaaS offerings use dedicated ML models and other logic for PII detection and often have better entity coverage or accuracy than Presidio.

Based on our internal research, leveraging Presidio in parallel to 3rd party PII detection services like Azure AI Language can bring optimal results mainly when the data in hand has entity types or values not supported by the 3rd party service. ([see example here](https://data-privacy-stack.github.io/presidio/samples/python/text_analytics/)).

## Using Presidio

### How can I start using Presidio?

1. Check out the [installation docs](https://data-privacy-stack.github.io/presidio/installation/).
2. Take a look at the [different samples](https://data-privacy-stack.github.io/presidio/samples/).
3. Try the [demo website](https://huggingface.co/spaces/presidio/presidio_demo).

### What are the main building blocks in Presidio?

Presidio is a suite built of several packages and building blocks:

1. [Presidio Analyzer](https://data-privacy-stack.github.io/presidio/analyzer/): a package for detecting PII entities in natural language.
2. [Presidio Anonymizer](https://data-privacy-stack.github.io/presidio/anonymizer/): a package for manipulating PII entities in text (e.g. remove, redact, hash, encrypt).
3. [Presidio Image Redactor](https://data-privacy-stack.github.io/presidio/image-redactor/): A package for detecting PII entities in image using OCR.
4. [Presidio Structured](https://data-privacy-stack.github.io/presidio/structured/): A package for detecting PII entities in structured/semi-structured data.
5. A set of sample deployments as Python packages or Docker containers for Kubernetes, Azure Data Factory, Spark and more.

## Customizing Presidio

### How can Presidio be customized to my needs?

Users can customize Presidio in multiple ways:

1. Create new or updated PII recognizers ([docs](https://data-privacy-stack.github.io/presidio/analyzer/adding_recognizers/)).
2. Adapt Presidio to new languages ([docs](https://data-privacy-stack.github.io/presidio/analyzer/languages/)).
3. Leverage state of the art Named Entity Recognition models ([docs](https://data-privacy-stack.github.io/presidio/analyzer/customizing_nlp_models/)).
4. Add new types of anonymizers ([docs](https://data-privacy-stack.github.io/presidio/anonymizer/adding_operators/)).
5. Create PII analysis and anonymization pipelines on different environments using Docker or Python ([samples](https://data-privacy-stack.github.io/presidio/samples/)).

And more.

### What NLP frameworks does Presidio support?

Presidio supports spaCy version 3+ for Named Entity Recognition, tokenization, lemmatization and more. We also support [Stanza](https://stanfordnlp.github.io/stanza/) using the [spacy-stanza](https://spacy.io/universe/project/spacy-stanza) package, and it is further possible to create PII recognizers leveraging other frameworks like [transformers](https://huggingface.co/transformers/usage.html#named-entity-recognition) or [Flair](https://github.com/flairNLP/flair).

For more information, see the [docs](https://data-privacy-stack.github.io/presidio/analyzer/customizing_nlp_models/).

### Can Presidio be used for Pseudonymization?

Pseudonymization is a de-identification technique in which the real data is replaced with fake data in a reversible way. Since there are various ways and approaches for this, we provide a simple [sample](https://github.com/data-privacy-stack/presidio/blob/main/docs/samples/python/example_custom_lambda_anonymizer.py) which can be extended for more sophisticated usage. If you have a question or a request on this topic, please open an issue on the repo.

### Does Presidio work on structured/tabular data?

[Presidio-structured](https://data-privacy-stack.github.io/presidio/structured/) is a capability in Presidio for detecting PII entities in structured/semi-structured data. It scans datasets for PII using Presidio Analyzer, and supports the redaction of text, cells, or columns in a tabular dataset.

## Improving detection accuracy

### What can I do if Presidio does not detect some of the PII entities in my data (False Negatives)?

Presidio comes loaded with several PII recognizers (see [list here](https://data-privacy-stack.github.io/presidio/supported_entities/)),
however its main strength lies in its customization capabilities to new entities, specific datasets, file types, languages or use cases.

### What can I do if Presidio falsely detects text as PII entities (False Positives)?

Some PII recognizers are less specific than others. A driver's license number, for example, could be any 9-digit number.
While Presidio leverages context words and other logic to improve the detection quality,
it could still falsely detect non-entity values as PII entities.

In order to avoid false positives, one could try to:

1. Change the acceptance threshold, which defines what is the minimum confidence value for a detected entity to be returned.
2. Remove unnecessary PII recognizers, if the dataset does not contain these entities.
3. Update/replace the logic of specific recognizers to better suit a specific dataset or use case.
4. Replace PII recognizers with those coming from 3rd party services.

Every PII identification logic would have its errors, and there is a trade-off between false positives (falsely detected text) and false negatives (PII entities which are not detected).

### How can I evaluate the performance of my Presidio instance?

In addition to Presidio, we maintain a repo focused on evaluation of models and PII recognizers [here](https://github.com/data-privacy-stack/presidio-research). It also features a simple PII data generator.

## Deployment

### How can I deploy Presidio into my environment?

The main Presidio modules (analyzer, anonymizer, image-redactor) can be used both as a Python package and as a dockerized REST API. See the [different deployment samples](https://data-privacy-stack.github.io/presidio/samples/) for example deployments.

!!! warning "Authentication and Authorization"
    Presidio API endpoints do not include built-in authentication by design. The containers are intentionally kept lean to allow flexibility for different deployment scenarios. Authentication and authorization should be implemented at a separate infrastructure layer (e.g., an API gateway, reverse proxy, or service mesh) according to your specific use case and security requirements. It is strongly recommended not to expose Presidio services directly to untrusted networks without an authentication layer in front of them.

## Contributing

### How can I contribute to Presidio?

First, review the [contribution guidelines](https://github.com/data-privacy-stack/presidio/blob/main/CONTRIBUTING.md), and feel free to reach out by opening an issue, posting a discussion or emailing us at <presidio@dataprivacystack.org>

### How can I report security vulnerabilities?

Please see the [security information](https://github.com/data-privacy-stack/presidio/blob/main/SECURITY.md).
