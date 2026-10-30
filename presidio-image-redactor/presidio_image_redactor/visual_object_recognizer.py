from abc import ABC, abstractmethod
from typing import List

from presidio_image_redactor.entities import ImageRecognizerResult


class VisualObjectRecognizer(ABC):
    """Recognizer of non-textual PII objects (e.g. faces) in a given image.

    Unlike the OCR based flow, a visual object recognizer does not go through
    ``presidio_analyzer``: the detected entity is a region of the image rather
    than a span of text. Implementations therefore return
    ``ImageRecognizerResult`` objects with ``start = end = 0``, since there is
    no text offset to map the entity to.

    The recommended entity types are ``"FACE"`` and ``"LICENSE_PLATE"``.
    Bounding boxes must be in the pixel coordinates of the image passed to
    ``recognize``.
    """

    @abstractmethod
    def recognize(self, image: object) -> List[ImageRecognizerResult]:
        """Detect visual PII objects in a given image.

        :param image: PIL Image/numpy array or file path(str) to be processed

        :return: list of detected entities with image bounding boxes
        """
        pass
