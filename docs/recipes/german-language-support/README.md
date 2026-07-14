# German Language Support

> **Domain**: Healthcare, Legal, Finance, General
> **Data Type**: German-language free text (medical documents, contracts, invoices, ID documents)
> **Goal**: Detect German PII and sensitive identifiers using Presidio's built-in German recognizers with a bilingual spaCy NLP engine

## Overview

**Domain**: Healthcare / Legal / Finance
**Data Type**: German-language documents
**Goal**: Detect German PII — including healthcare identifiers, tax numbers, official document numbers, and vehicle plates — using the German spaCy model alongside the English model so that bilingual (EN + DE) documents are handled correctly.

This recipe provides:

- `spacy_en_de.yaml` — a ready-to-use NLP engine configuration that loads both `en_core_web_lg` and `de_core_news_md`
- An overview of all German-specific recognizers available in Presidio

## Quick Start

### Prerequisites

```bash
pip install presidio-analyzer presidio-anonymizer
python -m spacy download en_core_web_lg
python -m spacy download de_core_news_md
```

### Sample Data

```python
sample_text = """
Sehr geehrter Herr Müller,

Ihre Krankenversicherungsnummer (KVNR): A123456780
Steuer-IdNr.: 86095742719
Arztnummer (LANR): 123456601
Betriebsstättennummer (BSNR): 021234568
USt-IdNr.: DE136695976
Führerscheinnummer: BO12345678A
Reisepassnummer: C01234565
"""
```

### Basic Configuration

```python
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

# Load the bilingual EN + DE spaCy configuration
provider = NlpEngineProvider(conf_file="spacy_en_de.yaml")
nlp_engine = provider.create_engine()

analyzer = AnalyzerEngine(
    nlp_engine=nlp_engine,
    supported_languages=["en", "de"],
)
anonymizer = AnonymizerEngine()

# Analyze German text
results = analyzer.analyze(text=sample_text, language="de")
anonymized = anonymizer.anonymize(text=sample_text, analyzer_results=results)

print(anonymized.text)
```

## Approach

Presidio ships pattern-based recognizers for 13 German entity types (see table below).
Each recognizer targets a single entity, uses `\b`-anchored regex patterns with
base confidence between 0.2 and 0.5, and relies on:

1. **Context words** (German terminology near the match) to boost confidence
2. **Check digit validation** where the official specification defines one
   (KVNR, Rentenversicherungsnummer, Steuer-IdNr., LANR)

The spaCy `de_core_news_md` model adds named-entity recognition for PERSON,
LOCATION, and ORGANIZATION on top of the pattern recognizers.

### Supported German Entities

| Entity | Name | Check digit |
|--------|------|-------------|
| `DE_TAX_ID` | Steueridentifikationsnummer | ✅ ISO 7064 Mod 11,10 |
| `DE_TAX_NUMBER` | Steuernummer (Länder format) | – |
| `DE_SOCIAL_SECURITY` | Rentenversicherungsnummer | ✅ DRV algorithm |
| `DE_HEALTH_INSURANCE` | Krankenversicherungsnummer (KVNR) | ✅ GKV-Spitzenverband |
| `DE_PASSPORT` | Reisepassnummer | – |
| `DE_ID_CARD` | Personalausweisnummer | – |
| `DE_KFZ` | Kfz-Kennzeichen | – |
| `DE_PLZ` | Postleitzahl | – |
| `DE_HANDELSREGISTER` | Handelsregisternummer | – |
| `DE_LANR` | Lebenslange Arztnummer | ✅ KBV weights algorithm |
| `DE_BSNR` | Betriebsstättennummer | – |
| `DE_VAT_ID` | Umsatzsteuer-Identifikationsnummer | – |
| `DE_FUEHRERSCHEIN` | Führerscheinnummer (post-2013) | – |

## Results

Formal evaluation against a labelled German dataset has not yet been performed.
To benchmark this recipe follow the [Presidio Research evaluation workflow](https://github.com/data-privacy-stack/presidio-research/blob/master/notebooks/4_Evaluate_Presidio_Analyzer.ipynb):

1. Generate synthetic German text with the [data generator](https://github.com/data-privacy-stack/presidio-research/blob/master/notebooks/1_Generate_data.ipynb)
2. Configure the analyzer with `spacy_en_de.yaml`
3. Run the evaluator and report precision / recall / F₂ / latency

**Precision**: TBD
**Recall**: TBD
**F₂ Score**: TBD
**Latency**: TBD

### Key Findings

- Recognizers with check digit validation (KVNR, RVNR, Steuer-IdNr., LANR) achieve
  very low false-positive rates even on ambiguous digit strings.
- Recognizers without a checksum (BSNR, PLZ, KFZ) rely heavily on context words;
  setting `score_threshold=0.5` when no context is present is recommended.
- The `DE_PLZ` (postal code) and `DE_KFZ` (vehicle plate) recognizers overlap with
  generic patterns; use the `entities` parameter to restrict detection when only
  specific entity types are needed.

## Tips for Others

- **Set `score_threshold`** to 0.4–0.5 for production use to filter out low-confidence
  pattern-only matches from context-free digit strings.
- **Use the `entities` parameter** to limit detection to the entity types relevant to
  your domain (e.g. only healthcare identifiers in clinical notes).
- **Pre-2013 Führerschein** numbers use locally defined, non-standardized formats that
  are not covered by `DE_FUEHRERSCHEIN`; handle them with a custom recognizer if needed.
- **DE_TELEMATIK_ID** was evaluated and rejected as a generic recognizer: the format
  (`\d{1,2}-<up to 128 chars>`) is too ambiguous for reliable free-text detection.

---

**Author**: MvdB
**Date**: 2026-03-19
