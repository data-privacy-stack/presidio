# Contributing to Presidio Recipes Gallery

Thank you for your interest in contributing! Recipes help others learn how to customize Presidio for specific domains.

## What Makes a Good Recipe?

A good recipe should:

1. **Focus on a Specific Domain**: Target a well-defined scenario (e.g., "Financial chatbot logs", "Clinical notes", "Customer support tickets")

2. **Be Reproducible**: Include working code that others can run

3. **Follow the Research Pattern**: Build upon the end-to-end approach from [presidio-research](https://github.com/data-privacy-stack/presidio-research), showing:
   - **Data Synthesis**: How to generate or obtain test data
   - **Configuration**: Your Presidio setup with any custom recognizers
   - **Evaluation**: Metrics (precision, recall, F₂) showing performance

4. **Keep It Simple**: Focus on getting a working example first. Detailed documentation can come later.

## Recipe Format

### Follow Presidio Research Examples

Your recipe should follow the end-to-end evaluation approach from [presidio-research](https://github.com/data-privacy-stack/presidio-research).

**Key reference notebooks:**
- [Evaluate Presidio Analyzer](https://github.com/data-privacy-stack/presidio-research/blob/master/notebooks/4_Evaluate_Presidio_Analyzer.ipynb) - Complete evaluation workflow example
- [Generate Synthetic Data](https://github.com/data-privacy-stack/presidio-research/blob/master/notebooks/1_Generate_data.ipynb) - Using Presidio Evaluator data generator

### Option 1: Single Jupyter Notebook (Recommended for Simple Cases)

For straightforward examples, use one notebook:

```
your-recipe-name/
├── recipe.ipynb          # Main notebook with data synthesis → evaluation
└── README.md             # Brief overview (optional)
```

### Option 2: Multiple Files (Recommended for Complex Flows)

For complex scenarios, break into separate files:

```
your-recipe-name/
├── 1_generate_data.ipynb # Data synthesis (use Presidio Evaluator or custom)
├── 2_configure.ipynb     # Presidio setup with custom recognizers
├── 3_evaluate.ipynb      # Run evaluation and analysis
└── README.md             # Overview and instructions
```

Or as Python scripts:

```
your-recipe-name/
├── generate_data.py      # Generate test data
├── configure.py          # Presidio setup
├── evaluate.py           # Run evaluation
└── README.md             # Overview
```

### Required Components

Your recipe should include:
- **Data Synthesis**: Generate synthetic data using [Presidio Evaluator](https://github.com/data-privacy-stack/presidio-research/blob/master/notebooks/1_Generate_data.ipynb) or your own method
- **Presidio Configuration**: Show your setup (default, custom recognizers, or custom models)
- **Evaluation**: Measure and report precision, recall, F₂ score, latency
- **Key Findings**: Brief summary of results and when to use this approach

## Quick Contribution Steps

1. **Fork the repo** and create a new branch

2. **Create your recipe folder** under `docs/recipes/your-recipe-name/`

3. **Use the template**: Copy `template.md` or start with a notebook

4. **Focus on working code first**: Don't worry about making it perfect

5. **Submit a PR**: We'll help refine it during review

## Evaluation Metrics

Include at minimum:
- **Precision**: Percentage of detected entities that were correct
- **Recall**: Percentage of actual PII that was detected  
- **F₂ Score**: Recall-weighted F-score (emphasizes catching all PII)
- **Latency**: Average processing time per sample

## Examples to Learn From

**Presidio Research Notebooks** (recommended starting point):
- [Evaluate Presidio Analyzer](https://github.com/data-privacy-stack/presidio-research/blob/master/notebooks/4_Evaluate_Presidio_Analyzer.ipynb) - Complete end-to-end evaluation example
- [Generate Synthetic Data](https://github.com/data-privacy-stack/presidio-research/blob/master/notebooks/1_Generate_data.ipynb) - Presidio Evaluator data generator
- [Other presidio-research notebooks](https://github.com/data-privacy-stack/presidio-research/tree/master/notebooks) - Additional examples and tools

**Additional Resources:**
- [Presidio Samples](../samples/index.md): Integration patterns and usage examples

## Questions?

- Open an issue with the `recipe` label
- Email [presidio@dataprivacystack.org](mailto:presidio@dataprivacystack.org)
- Tag @omri374 in your PR for guidance

## License

By contributing, you agree to license your work under the MIT License.
