"""Country-specific recognizers package."""

from .canada.ca_ramq_recognizer import CaRamqRecognizer
from .canada.ca_sin_recognizer import CaSinRecognizer

__all__ = [
    "CaRamqRecognizer",
    "CaSinRecognizer",
]
