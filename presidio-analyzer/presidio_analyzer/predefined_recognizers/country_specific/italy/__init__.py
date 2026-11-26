"""Italy-specific recognizers."""

from .it_driver_license_recognizer import ItDriverLicenseRecognizer
from .it_fiscal_code_recognizer import ItFiscalCodeRecognizer
from .it_identity_card_recognizer import ItIdentityCardRecognizer
from .it_license_plate_recognizer import ItLicensePlateRecognizer
from .it_passport_recognizer import ItPassportRecognizer
from .it_vat_code import ItVatCodeRecognizer

__all__ = [
    "ItFiscalCodeRecognizer",
    "ItDriverLicenseRecognizer",
    "ItIdentityCardRecognizer",
    "ItLicensePlateRecognizer",
    "ItPassportRecognizer",
    "ItVatCodeRecognizer",
]
