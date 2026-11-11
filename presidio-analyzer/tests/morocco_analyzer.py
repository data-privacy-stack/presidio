"""Run a Moroccan recognizer the way a user configures it.

The recognizer is enabled from the shipped YAML entry and analyzed in Arabic
or French. No Arabic or French model is installed in the test environment, so
the text is split by spaCy's rule-based tokenizers and each lemma is the
lowercased token.
"""

from functools import cache
from pathlib import Path

import presidio_analyzer
import spacy
import yaml
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpArtifacts, NoOpNlpEngine
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

LANGUAGES = ["ar", "fr"]


class RuleBasedTokensNlpEngine(NoOpNlpEngine):
    """Give the context enhancer real tokens without a language model."""

    def process_text(self, text: str, language: str) -> NlpArtifacts:
        """Tokenize the text with the rule-based tokenizer of the language."""
        doc = _tokenizer(language)(text)
        return NlpArtifacts(
            entities=[],
            tokens=doc,
            tokens_indices=[token.idx for token in doc],
            lemmas=[token.lower_ for token in doc],
            nlp_engine=self,
            language=language,
        )


@cache
def _tokenizer(language: str):
    return spacy.blank(language)


@cache
def analyzer_for(recognizer_name: str) -> AnalyzerEngine:
    """Build an analyzer with one recognizer enabled from the shipped YAML."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entry = next(r for r in recognizers if r.get("name") == recognizer_name)
    assert entry["country_code"] == "ma"
    assert entry["supported_languages"] == LANGUAGES

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": LANGUAGES,
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()
    nlp_engine = RuleBasedTokensNlpEngine(
        models=[{"lang_code": lang, "model_name": "no_op"} for lang in LANGUAGES]
    )
    return AnalyzerEngine(
        registry=registry, nlp_engine=nlp_engine, supported_languages=LANGUAGES
    )
