# Evaluating PII detection with Presidio

## Why evaluate PII detection?

No de-identification system is perfect.
It is important to evaluate the performance of a PII detection system for your specific use case.
This evaluation can help you understand where the system makes mistakes and how to iteratively improve the detection mechanisms,
which recognizers and models to use, and how to configure them.

## Common evaluation metrics

The most common evaluation metrics are [`precision`, `recall`](<https://en.wikipedia.org/wiki/Precision_and_recall>), and [`Fβ score`](<https://en.wikipedia.org/wiki/F-score>), which is a combination of precision and recall.
These metrics are calculated based on the number of true positives, false positives, and false negatives.
For every use case, the false positive and false negative rates should be balanced to achieve the desired level of accuracy.

- Precision measures the proportion of true positive results among the positive results: `TP / (TP + FP)`.
- Recall measures the proportion of true positive results among the actual positives: `TP / (TP + FN)`.
- Fβ score is a weighted harmonic mean of precision and recall: `(1 + β^2) * (precision * recall) / (β^2 * precision + recall)`.

[Click here for more definitions](https://en.wikipedia.org/wiki/Precision_and_recall#Definition).

!!! note "Note"
     In PII detection, recall is often more important than precision, as we'd like to avoid missing any PII.
     In such cases, we recommend to use the β=2 score, which gives more importance to recall.

## How to evaluate PII detection with Presidio

Presidio provides a set of tools to evaluate the performance of the PII detection system.
In addition, it provides simple data generation tools to help you create a dataset for evaluation.

### Evaluating the Presidio Analyzer using Presidio-Research

Presidio-Research is a python package with a set of tools that help you evaluate the performance of the Presidio Analyzer.
To get started, follow the instructions in the [Presidio-Research repository](https://github.com/data-privacy-stack/presidio-research).

The easiest way to get started is by reviewing the notebooks:

- [Notebook 1](https://github.com/data-privacy-stack/presidio-research/blob/master/notebooks/1_Generate_data.ipynb): Shows how to use the PII data generator.
- [Notebook 2](https://github.com/data-privacy-stack/presidio-research/blob/master/notebooks/2_PII_EDA.ipynb): Shows a simple analysis of the PII dataset.
- [Notebook 3](https://github.com/data-privacy-stack/presidio-research/blob/master/notebooks/3_Split_by_pattern_number.ipynb): Provides tools to split the dataset into train/test/validation sets while avoiding leakage due to the same pattern appearing in multiple folds (only applicable for synthetically generated data).
- [Notebook 4](https://github.com/data-privacy-stack/presidio-research/blob/master/notebooks/4_Evaluate_Presidio_Analyzer.ipynb): Shows how to use the evaluation tools to evaluate how well Presidio detects PII. Note that this is using the vanilla Presidio, and the results aren't very accurate.
- [Notebook 5](https://github.com/data-privacy-stack/presidio-research/blob/master/notebooks/5_Evaluate_Custom_Presidio_Analyzer.ipynb): Shows how one can configure Presidio to detect PII much more accurately, and boost the f score in ~30%.

For more information and advanced usage, refer to the [Presidio-Research repository](https://github.com/data-privacy-stack/presidio-research).

### Evaluating DICOM redaction with Presidio Image Redactor

See [Evaluating DICOM redaction](../image-redactor/evaluating_dicom_redaction.md) for more information.
For a full demonstration, see the [evaluation notebook](../samples/python/example_dicom_redactor_evaluation.ipynb).
