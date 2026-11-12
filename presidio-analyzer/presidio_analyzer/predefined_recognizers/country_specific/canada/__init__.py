"""Canada-specific recognizers package."""

from .ca_postal_code_recognizer import CaPostalCodeRecognizer
from .ca_ramq_recognizer import CaRamqRecognizer
from .ca_sin_recognizer import CaSinRecognizer

__all__ = [
    "CaPostalCodeRecognizer",
    "CaRamqRecognizer",
    "CaSinRecognizer",
]
