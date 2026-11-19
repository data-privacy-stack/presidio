"""Spain-specific recognizers package."""

from .es_ccc_recognizer import EsCccRecognizer
from .es_cif_recognizer import EsCifRecognizer
from .es_nie_recognizer import EsNieRecognizer
from .es_nif_recognizer import EsNifRecognizer
from .es_nss_recognizer import EsNssRecognizer
from .es_passport_recognizer import EsPassportRecognizer

__all__ = [
    "EsCifRecognizer",
    "EsNifRecognizer",
    "EsNieRecognizer",
    "EsPassportRecognizer",
    "EsNssRecognizer",
    "EsCccRecognizer",
]
