"""Philippines-specific recognizers."""

from .ph_passport_recognizer import PhPassportRecognizer
from .ph_tin_recognizer import PhTinRecognizer

__all__ = [
    "PhPassportRecognizer", "PhTinRecognizer"
]
