"""Philippines-specific recognizers package."""

from .ph_tin_recognizer import PhTinRecognizer
from .ph_umid_recognizer import PhUmidRecognizer

__all__ = [
    "PhTinRecognizer",
    "PhUmidRecognizer",
]
