# Recipe Template: [Recipe Name]

> **Note**: This is a simplified template for contributing recipes. Focus on providing a working example - detailed documentation can come later.

## Overview

**Domain**: [e.g., Healthcare, Finance, Retail]  
**Data Type**: [e.g., Clinical notes, Chat logs, API responses]  
**Goal**: [What you're trying to detect and anonymize]

## Quick Start

### Sample Data

```python
# Example data that demonstrates the scenario
sample_text = """
[Your example text with PII]
"""
```

### Basic Configuration

```python
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

# Your Presidio configuration
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

# Analyze and anonymize
results = analyzer.analyze(text=sample_text, language="en")
anonymized = anonymizer.anonymize(text=sample_text, analyzer_results=results)

print(anonymized.text)
```

## Approach

Describe your approach in a few sentences. What recognizers, models, or techniques did you use?

## Results

**Precision**: [0.XX]  
**Recall**: [0.XX]  
**F₂ Score**: [0.XX]  
**Latency**: [XX ms/sample]

### Key Findings

- [Main insight 1]
- [Main insight 2]
- [Main insight 3]

## End-to-End Example

### Recommended Approach: Follow Presidio Research Patterns

Provide an end-to-end example following the patterns from [presidio-research](https://github.com/data-privacy-stack/presidio-research):

**Reference notebooks:**
- [Evaluate Presidio Analyzer](https://github.com/data-privacy-stack/presidio-research/blob/master/notebooks/4_Evaluate_Presidio_Analyzer.ipynb) - Complete evaluation workflow
- [Generate Synthetic Data](https://github.com/data-privacy-stack/presidio-research/blob/master/notebooks/1_Generate_data.ipynb) - Using Presidio Evaluator data generator

**Structure your example:**

1. **Data Synthesis**: Generate synthetic data using [Presidio Evaluator](https://github.com/data-privacy-stack/presidio-research/blob/master/notebooks/1_Generate_data.ipynb) or your own method
2. **Configuration**: Set up Presidio with your custom recognizers or models
3. **Evaluation**: Measure precision, recall, and F₂ score
4. **Analysis**: Discuss results and trade-offs

### Format Options

- **Single Jupyter Notebook**: Best for simple, focused examples (recommended for most recipes)
- **Multiple Files**: For complex flows, break into separate notebooks or Python scripts:
  ```
  your-recipe-name/
  ├── 1_generate_data.ipynb    # Data synthesis
  ├── 2_configure.ipynb         # Presidio setup
  ├── 3_evaluate.ipynb          # Evaluation
  └── README.md                 # Overview
  ```

## Tips for Others

- [Tip 1: When this approach works best]
- [Tip 2: Common pitfalls to avoid]
- [Tip 3: How to adapt to similar scenarios]

---

**Author**: [Your Name]  
**Date**: [YYYY-MM-DD]
