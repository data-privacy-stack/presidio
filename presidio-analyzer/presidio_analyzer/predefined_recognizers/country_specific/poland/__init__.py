"""Poland-specific recognizers."""

from .pl_id_card_recognizer import PlIdCardRecognizer
from .pl_pesel_recognizer import PlPeselRecognizer

__all__ = [
    "PlIdCardRecognizer",
    "PlPeselRecognizer",
]
