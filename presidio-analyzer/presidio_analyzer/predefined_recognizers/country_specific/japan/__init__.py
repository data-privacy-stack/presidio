"""Japan-specific recognizers."""

from .jp_corporate_number_recognizer import JpCorporateNumberRecognizer
from .jp_my_number_recognizer import JpMyNumberRecognizer

__all__ = [
    "JpCorporateNumberRecognizer",
    "JpMyNumberRecognizer",
]
