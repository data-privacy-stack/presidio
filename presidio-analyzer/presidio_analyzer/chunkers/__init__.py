"""Text chunking strategies for handling long texts."""

from presidio_analyzer.chunkers.base_chunker import BaseTextChunker, TextChunk
from presidio_analyzer.chunkers.character_based_text_chunker import (
    CharacterBasedTextChunker,
)
from presidio_analyzer.chunkers.text_chunker_provider import TextChunkerProvider

__all__ = [
    "BaseTextChunker",
    "TextChunk",
    "CharacterBasedTextChunker",
    "TextChunkerProvider",
]
