"""Nigeria-specific recognizers."""

from .ng_bvn_recognizer import NgBvnRecognizer
from .ng_nin_recognizer import NgNinRecognizer
from .ng_vehicle_registration_recognizer import NgVehicleRegistrationRecognizer

__all__ = [
    "NgBvnRecognizer",
    "NgNinRecognizer",
    "NgVehicleRegistrationRecognizer",
]

