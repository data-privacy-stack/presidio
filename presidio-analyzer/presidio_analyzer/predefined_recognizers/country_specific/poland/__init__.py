"""Poland-specific recognizers."""

from .pl_pesel_recognizer import PlPeselRecognizer
from .pl_regon_recognizer import PlRegonRecognizer

__all__ = [
    "PlPeselRecognizer",
    "PlRegonRecognizer",
]
