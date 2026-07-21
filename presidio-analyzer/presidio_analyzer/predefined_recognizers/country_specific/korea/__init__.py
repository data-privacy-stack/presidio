"""Korea-specific recognizers."""

from .kr_brn_recognizer import KrBrnRecognizer
from .kr_crn_recognizer import KrCrnRecognizer
from .kr_driver_license_recognizer import KrDriverLicenseRecognizer
from .kr_frn_recognizer import KrFrnRecognizer
from .kr_passport_recognizer import KrPassportRecognizer
from .kr_rrn_recognizer import KrRrnRecognizer

__all__ = [
    "KrBrnRecognizer",
    "KrCrnRecognizer",
    "KrDriverLicenseRecognizer",
    "KrFrnRecognizer",
    "KrPassportRecognizer",
    "KrRrnRecognizer",
]
