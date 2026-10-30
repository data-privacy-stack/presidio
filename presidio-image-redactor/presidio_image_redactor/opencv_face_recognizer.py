from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from presidio_image_redactor.entities import ImageRecognizerResult
from presidio_image_redactor.visual_object_recognizer import VisualObjectRecognizer

DEFAULT_CASCADE_FILE = "haarcascade_frontalface_default.xml"


class OpenCVFaceRecognizer(VisualObjectRecognizer):
    """Detect faces in an image using an OpenCV Haar cascade classifier.

    Detected faces are returned as ``FACE`` entities with ``start = end = 0``.

    The default classifier is ``haarcascade_frontalface_default.xml``, shipped
    with opencv-python under ``cv2.data.haarcascades``. It implements the
    Viola-Jones cascade of boosted Haar-like features (Lienhart & Maydt, 2002,
    "An extended set of Haar-like features for rapid object detection") and
    detects *frontal* faces only: profiles, strongly rotated or occluded faces
    are missed.

    Haar cascades do not produce a calibrated confidence, so every detection is
    reported with the same ``score`` value, which is a constructor parameter.

    :param cascade_path: path to the Haar cascade XML file. Defaults to the
        frontal-face cascade bundled with opencv-python.
    :param scale_factor: how much the image size is reduced at each cascade
        scale (``scaleFactor`` of ``detectMultiScale``).
    :param min_neighbors: how many neighbors each candidate rectangle needs to
        be retained. Higher values yield fewer detections of higher quality.
    :param min_size: minimum face size in pixels (width, height).
    :param score: the fixed score assigned to every detected face.
    """

    def __init__(
        self,
        cascade_path: Optional[str] = None,
        scale_factor: float = 1.1,
        min_neighbors: int = 5,
        min_size: Tuple[int, int] = (30, 30),
        score: float = 0.85,
    ):
        if not cascade_path:
            cascade_path = cv2.data.haarcascades + DEFAULT_CASCADE_FILE

        self.classifier = cv2.CascadeClassifier(cascade_path)
        if self.classifier.empty():
            raise ValueError(f"Could not load a Haar cascade from {cascade_path}")

        self.cascade_path = cascade_path
        self.scale_factor = scale_factor
        self.min_neighbors = min_neighbors
        self.min_size = min_size
        self.score = score

    def recognize(self, image: object) -> List[ImageRecognizerResult]:
        """Detect faces in a given image.

        :param image: PIL Image/numpy array or file path(str) to be processed

        :return: list of detected faces with image bounding boxes
        """
        greyscale_image = self._to_greyscale(image)
        faces = self.classifier.detectMultiScale(
            greyscale_image,
            scaleFactor=self.scale_factor,
            minNeighbors=self.min_neighbors,
            minSize=self.min_size,
        )

        return [
            ImageRecognizerResult(
                "FACE", 0, 0, self.score, int(left), int(top), int(width), int(height)
            )
            for left, top, width, height in faces
        ]

    @staticmethod
    def _to_greyscale(image: object) -> np.ndarray:
        """Convert the supported image types to a greyscale numpy array.

        :param image: PIL Image/numpy array or file path(str) to be converted

        :return: the image as a single channel numpy array
        """
        if isinstance(image, str):
            with Image.open(image) as opened_image:
                return np.array(opened_image.convert("L"))

        if isinstance(image, Image.Image):
            return np.array(image.convert("L"))

        if isinstance(image, np.ndarray):
            if image.ndim == 2:
                return image
            if image.ndim == 3:
                conversion = (
                    cv2.COLOR_RGBA2GRAY if image.shape[2] == 4 else cv2.COLOR_RGB2GRAY
                )
                return cv2.cvtColor(image, conversion)

        raise ValueError(
            "image must be a PIL Image, a 2D or 3D numpy array or a file path"
        )
