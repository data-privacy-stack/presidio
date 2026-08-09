# Recipes Gallery

Welcome to the Presidio Recipes Gallery! This section provides curated, end-to-end examples demonstrating how to customize Presidio for specific data privacy and de-identification scenarios.

## What are Recipes?

Recipes are comprehensive, reproducible examples tailored to common data domains and use cases. Each recipe goes beyond basic documentation to provide:

1. **Real-world Context**: Focused on specific scenarios like financial chatbot conversations, clinical notes, REST API logs, or multilingual content
2. **Synthetic Data Generation**: Methods for creating realistic test data that mimics your production environment
3. **Performance Benchmarks**: Evaluation metrics (precision, recall, F₂ score, and latency) across different Presidio configurations
4. **Progressive Complexity**: Examples ranging from out-of-the-box usage to advanced customization with transformers, LLMs, or hybrid approaches

## Why Use Recipes?

While Presidio's documentation covers the fundamentals, recipes bridge the gap between generic examples and production-ready implementations. They help you:

- **Evaluate Performance**: Understand Presidio's accuracy and speed for your specific domain before deployment
- **Customize Effectively**: Learn which recognizers, models, and configurations work best for different data types
- **Compare Approaches**: See side-by-side comparisons of different implementation strategies
- **Reduce Development Time**: Start with a working example close to your use case instead of building from scratch

## Recipe Structure

Each recipe typically includes:

- **Scenario Description**: The domain and data type
- **Data Synthesis**: Methods for generating test data using [Presidio Evaluator](https://github.com/data-privacy-stack/presidio-research/blob/master/notebooks/1_Generate_data.ipynb) or custom methods
- **Configuration**: Presidio setup with any custom recognizers or models
- **Evaluation**: Performance metrics (precision, recall, F₂ score, latency)
- **Implementation**: Jupyter notebook or Python scripts showing the end-to-end flow (see [example](https://github.com/data-privacy-stack/presidio-research/blob/master/notebooks/4_Evaluate_Presidio_Analyzer.ipynb))
- **Key Findings**: When to use this approach and trade-offs to consider

For complex flows, consider breaking into multiple notebooks or scripts for better organization.

## Available Recipes

Currently, the recipes gallery is being built. Check back soon for recipes covering:

- **Financial Domain**: Chat conversations, transaction logs, customer service interactions
- **Healthcare Domain**: Clinical notes, patient records, medical reports
- **Retail/E-commerce**: Customer data, order information, support tickets
- **Enterprise**: REST API logs, database exports, internal communications
- **Multilingual**: Examples for Spanish, French, German, and other languages

## Recipe Performance Table (Coming Soon)

We're developing a comprehensive benchmark table that will show Presidio's performance across different domains and implementation levels. The table will include:

| Domain / Scenario | Out-of-the-box (spaCy) | Augmented (+ custom recognizers) | Custom Model (ML/Transformer) | Hybrid "Best-Effort" (ensemble/LLM) |
|-------------------|------------------------|----------------------------------|--------------------------------|-------------------------------------|
| **Financial (Chatbot)** | Coming Soon | Coming Soon | Coming Soon | Coming Soon |
| **Medical (Clinical Notes)** | Coming Soon | Coming Soon | Coming Soon | Coming Soon |
| **Retail (JSON REST)** | Coming Soon | Coming Soon | Coming Soon | Coming Soon |
| **Multilingual (Spanish)** | Coming Soon | Coming Soon | Coming Soon | Coming Soon |

Each cell will contain:
- **P** = Precision
- **R** = Recall  
- **F₂** = F₂ score (recall-weighted F-score)
- **Latency** = Average processing time per sample (milliseconds)
- **Notebook** = Link to interactive Jupyter notebook

## How to Use a Recipe

1. **Browse the recipes** to find one matching your domain or use case
2. **Review the notebook** to understand the approach and results
3. **Run the notebook** in your environment to reproduce the results
4. **Adapt the configuration** to your specific data and requirements
5. **Evaluate performance** on your own test dataset
6. **Deploy** the configuration that best meets your accuracy and performance needs

## Contributing a Recipe

We welcome community contributions! See our [contribution guidelines](CONTRIBUTING.md) for details.

**Reference Examples:**
- [Evaluate Presidio Analyzer](https://github.com/data-privacy-stack/presidio-research/blob/master/notebooks/4_Evaluate_Presidio_Analyzer.ipynb) - Complete end-to-end evaluation workflow
- [Generate Synthetic Data](https://github.com/data-privacy-stack/presidio-research/blob/master/notebooks/1_Generate_data.ipynb) - Presidio Evaluator data generator

Follow the pattern: **Data Synthesis** → **Configuration** → **Evaluation**

For complex flows, break into multiple notebooks or scripts. Focus on getting working code first - we'll help refine documentation during review.

## Related Resources

- [Presidio Samples](../samples/index.md): Additional usage examples and integration patterns
- [Tutorial Series](../tutorial/index.md): Step-by-step guide to Presidio features
- [Best Practices for Developing Recognizers](../analyzer/developing_recognizers.md): Deep dive into creating custom PII recognizers
- [Presidio Research Repository](https://github.com/data-privacy-stack/presidio-research): Evaluation tools and research datasets
- [FAQ](../faq.md): Common questions about improving detection accuracy

## Questions or Feedback?

If you have questions about recipes or suggestions for new scenarios to cover, please:

- Open an issue on [GitHub](https://github.com/data-privacy-stack/presidio/issues)
- Email us at [presidio@dataprivacystack.org](mailto:presidio@dataprivacystack.org)
- Join the discussion in our [community channels](../community.md)

---

**Note**: The recipes gallery demonstrates Presidio's flexibility and customization capabilities. The goal is to show that Presidio is designed to be adapted to your specific needs, not used as a one-size-fits-all solution. Each recipe illustrates best practices for customization in different contexts.
