# Supporting new types of PII operators

Operators are the presidio-anonymizer actions over the text.

There are two types of operators:

- Anonymize (e.g., hash, replace, redact, encrypt, mask)
- Deanonymize (e.g., decrypt)

Presidio anonymizer can be easily extended to support additional anonymization and deanonymization methods (called Operators).

## Extending presidio-anonymizer for additional PII operators

1. Create new python class implementing the abstract [Operator](https://github.com/data-privacy-stack/presidio/blob/main/presidio-anonymizer/presidio_anonymizer/operators/operator.py) class.
2. Implement the methods:
    - `operate` - gets the data and returns a new text expected to replace the old one.
    - `validate` - validate the parameters entered for the anonymizer exists and valid.
    - `operator_name` - this method helps to automatically load the existing anonymizers.
    - `operator_type` - either Anonymize or Deanonymize. Will be mapped to the proper engine.
3. Call the `AnonymizerEngine.add_anonymizer` method to add a new  operator to the anonymizer. Alternatively, call the `DeanonymizeEngine.add_deanonymizer` method to add a new deanonymizer.

See a detailed example [here](../samples/python/pseudonymization.ipynb).
