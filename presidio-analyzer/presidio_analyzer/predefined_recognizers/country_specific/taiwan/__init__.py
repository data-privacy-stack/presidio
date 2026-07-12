"""Taiwan-specific predefined recognizers."""

from .tw_national_id_recognizer import TwNationalIdRecognizer
from .tw_phone_number_recognizer import TwPhoneNumberRecognizer

__all__ = [
    "TwNationalIdRecognizer",
    "TwPhoneNumberRecognizer",
]
