"""Presidio engine construction for DatOnym."""

from __future__ import annotations

from pathlib import Path

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.analyzer_engine_provider import AnalyzerEngineProvider
from presidio_anonymizer import AnonymizerEngine

from datonym_gateway.operators import DatonymTokenAnonymizer


def build_analyzer(config_path: Path) -> AnalyzerEngine:
    """Create an AnalyzerEngine from the DatOnym German configuration."""

    return AnalyzerEngineProvider(analyzer_engine_conf_file=config_path).create_engine()


def build_anonymizer() -> AnonymizerEngine:
    """Create an AnonymizerEngine with the DatOnym token operator installed."""

    anonymizer = AnonymizerEngine()
    anonymizer.add_anonymizer(DatonymTokenAnonymizer)
    return anonymizer
