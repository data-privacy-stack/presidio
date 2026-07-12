# Presidio structured

## Description

The Presidio structured package is a flexible and customizable framework designed to identify and protect structured sensitive data. This tool extends the capabilities of Presidio, focusing on structured data formats such as tabular formats and semi-structured formats (JSON). It leverages the detection capabilities of Presidio-Analyzer to identify columns or keys containing personally identifiable information (PII), and establishes a mapping between these column/keys names and the detected PII entities. Following the detection, Presidio-Anonymizer is used to apply de-identification techniques to each value in columns identified as containing PII, ensuring the sensitive data is appropriately protected.

## Installation

### As a python package

To install the `presidio-structured` package, run the following command:

```sh
pip install presidio-structured
```

### Getting started

Anonymizing Data Frames:

```py
import pandas as pd
from presidio_structured import StructuredEngine, PandasAnalysisBuilder
from presidio_anonymizer.entities import OperatorConfig
from faker import Faker # optionally using faker as an example

# Initialize the engine with a Pandas data processor (default)
pandas_engine = StructuredEngine()

# Create a sample DataFrame
sample_df = pd.DataFrame({'name': ['John Doe', 'Jane Smith'], 'email': ['john.doe@example.com', 'jane.smith@example.com']})

# Generate a tabular analysis which describes PII entities in the DataFrame.
tabular_analysis = PandasAnalysisBuilder().generate_analysis(sample_df)

# Define anonymization operators
fake = Faker()
operators = {
    "PERSON": OperatorConfig("replace", {"new_value": "REDACTED"}),
    "EMAIL_ADDRESS": OperatorConfig("custom", {"lambda": lambda x: fake.safe_email()})
}

# Anonymize DataFrame
anonymized_df = pandas_engine.anonymize(sample_df, tabular_analysis, operators=operators)
print(anonymized_df)
```

## More information

- [Docs](https://presidio.dataprivacystack.org/structured/)
- [Samples](https://github.com/data-privacy-stack/presidio/blob/main/docs/samples/python/example_structured.ipynb)
- [Join the discussion](https://github.com/data-privacy-stack/presidio/discussions?discussions_q=structured)
- [Review issues on Github](https://github.com/data-privacy-stack/presidio/issues?q=is%3Aissue+label%3Astructured-data)
