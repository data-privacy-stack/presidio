"""presidio-structured root module."""

import logging

from .analysis_builder import JsonAnalysisBuilder, PandasAnalysisBuilder
from .config import StructuredAnalysis
from .data import (
    CsvReader,
    JsonDataProcessor,
    JsonLinesReader,
    JsonReader,
    PandasDataProcessor,
)
from .structured_engine import StructuredEngine

logging.getLogger("presidio-structured").addHandler(logging.NullHandler())

__all__ = [
    "StructuredEngine",
    "JsonAnalysisBuilder",
    "PandasAnalysisBuilder",
    "StructuredAnalysis",
    "CsvReader",
    "JsonReader",
    "JsonLinesReader",
    "PandasDataProcessor",
    "JsonDataProcessor",
]
