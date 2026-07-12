# Presidio

[![Build Status](https://github.com/data-privacy-stack/presidio/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/data-privacy-stack/presidio/actions/workflows/ci.yml)
[![MIT license](https://img.shields.io/badge/license-MIT-brightgreen.svg)](http://opensource.org/licenses/MIT)

**Context aware, pluggable and customizable PII de-identification service for text and images.**

## Overview

`presidio` is a convenience meta-package that references and installs
[presidio-analyzer](https://pypi.org/project/presidio-analyzer/) and
[presidio-anonymizer](https://pypi.org/project/presidio-anonymizer/), the PII detection and
anonymization engines from the [Microsoft Presidio](https://github.com/data-privacy-stack/presidio) project.

> **Note:** This package contains no code of its own. It simply pulls in `presidio-analyzer` and
> `presidio-anonymizer` as dependencies. For the full feature set, documentation, and source code
> please refer to the
> [presidio-analyzer README](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/README.md)
> and the
> [presidio-anonymizer README](https://github.com/data-privacy-stack/presidio/blob/main/presidio-anonymizer/README.md).

## Installation

```bash
pip install presidio
```

This will install `presidio-analyzer`, `presidio-anonymizer`, and their dependencies.

## Usage

```python
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

results = analyzer.analyze(text="My name is John Doe", language="en")
anonymized = anonymizer.anonymize(text="My name is John Doe", analyzer_results=results)
print(anonymized)
```

## Documentation

For full documentation, visit [https://presidio.dataprivacystack.org](https://presidio.dataprivacystack.org).

## Acknowledgements

The idea of publishing a top-level `presidio` package that bundles `presidio-analyzer` and
`presidio-anonymizer` was originally proposed and implemented by
**Sakthi Santhosh Anumand** and **Harsha Vardhan**. We thank them for the initiative and for
making Presidio more accessible to the community.

## License

MIT License. See [LICENSE](https://github.com/data-privacy-stack/presidio/blob/main/LICENSE) for details.

