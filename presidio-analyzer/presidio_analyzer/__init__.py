# isort: skip_file
"""Presidio analyzer package."""

import logging

from presidio_analyzer.analysis_explanation import AnalysisExplanation
from presidio_analyzer.recognizer_result import RecognizerResult
from presidio_analyzer.dict_analyzer_result import DictAnalyzerResult
from presidio_analyzer.entity_recognizer import EntityRecognizer
from presidio_analyzer.local_recognizer import LocalRecognizer
from presidio_analyzer.pattern import Pattern
from presidio_analyzer.pattern_recognizer import PatternRecognizer
from presidio_analyzer.remote_recognizer import RemoteRecognizer
from presidio_analyzer.lm_recognizer import LMRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistry
from presidio_analyzer.analyzer_engine import AnalyzerEngine
from presidio_analyzer.batch_analyzer_engine import BatchAnalyzerEngine
from presidio_analyzer.analyzer_request import AnalyzerRequest
from presidio_analyzer.context_aware_enhancers import ContextAwareEnhancer
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer
from presidio_analyzer.context_aware_enhancers import PhraseContextAwareEnhancer
from presidio_analyzer.context_aware_enhancers import CompositeContextAwareEnhancer
from presidio_analyzer.analyzer_engine_provider import AnalyzerEngineProvider

# Define default loggers behavior

# 1. presidio_analyzer logger
logging.getLogger("presidio-analyzer").addHandler(logging.NullHandler())

# 2. decision_process logger.
# Setting the decision_process trace here as we would want it
# to be activated using a parameter to AnalyzeEngine and not by default.
decision_process_logger = logging.getLogger("decision_process")
ch = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s][%(name)s][%(levelname)s]%(message)s")
ch.setFormatter(formatter)
decision_process_logger.addHandler(ch)
decision_process_logger.setLevel("INFO")
__all__ = [
    "Pattern",
    "AnalysisExplanation",
    "RecognizerResult",
    "DictAnalyzerResult",
    "EntityRecognizer",
    "LocalRecognizer",
    "PatternRecognizer",
    "RemoteRecognizer",
    "LMRecognizer",
    "RecognizerRegistry",
    "AnalyzerEngine",
    "AnalyzerRequest",
    "ContextAwareEnhancer",
    "LemmaContextAwareEnhancer",
    "PhraseContextAwareEnhancer",
    "CompositeContextAwareEnhancer",
    "BatchAnalyzerEngine",
    "AnalyzerEngineProvider",
]
