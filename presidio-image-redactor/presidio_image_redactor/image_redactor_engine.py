from typing import List, Optional, Tuple, Union

import presidio_analyzer  # required for isinstance check which throws an error when trying to specify PatternRecognizer  # noqa: E501
from PIL import Image, ImageChops, ImageDraw
from presidio_analyzer import PatternRecognizer

from presidio_image_redactor import BboxProcessor, ImageAnalyzerEngine
from presidio_image_redactor.entities import ImageRecognizerResult


class ImageRedactorEngine:
    """ImageRedactorEngine performs OCR + PII detection + bounding box redaction.

    :param image_analyzer_engine: Engine which performs OCR + PII detection.
    """

    def __init__(
        self,
        image_analyzer_engine: ImageAnalyzerEngine = None,
    ):
        if not image_analyzer_engine:
            self.image_analyzer_engine = ImageAnalyzerEngine()
        else:
            self.image_analyzer_engine = image_analyzer_engine

        self.bbox_processor = BboxProcessor()

    def redact_and_return_bbox(
        self,
        image: Image.Image,
        fill: Union[int, Tuple[int, int, int]] = (0, 0, 0),
        ocr_kwargs: Optional[dict] = None,
        ad_hoc_recognizers: Optional[List[PatternRecognizer]] = None,
        **text_analyzer_kwargs,
    ) -> Tuple[Image.Image, List[ImageRecognizerResult]]:
        """Redact method to redact the given image and return the bboxes.

        Please notice, this method duplicates the image, creates a new instance and
        manipulate it.
        :param image: PIL Image to be processed.
        :param fill: colour to fill the shape - int (0-255) for
        grayscale or Tuple(R, G, B) for RGB.
        :param ocr_kwargs: Additional params for OCR methods.
        :param ad_hoc_recognizers: List of PatternRecognizer objects to use
        for ad-hoc recognizer.
        :param text_analyzer_kwargs: Additional values for the analyze method
        in AnalyzerEngine.

        :return: the redacted image and the list of bboxes
        """

        image = ImageChops.duplicate(image)

        # Check the ad-hoc recognizers list
        self._check_ad_hoc_recognizer_list(ad_hoc_recognizers)

        # Detect PII
        if ad_hoc_recognizers is None:
            bboxes = self.image_analyzer_engine.analyze(
                image,
                ocr_kwargs=ocr_kwargs,
                **text_analyzer_kwargs,
            )
        else:
            bboxes = self.image_analyzer_engine.analyze(
                image,
                ocr_kwargs=ocr_kwargs,
                ad_hoc_recognizers=ad_hoc_recognizers,
                **text_analyzer_kwargs,
            )

        draw = ImageDraw.Draw(image)

        for box in bboxes:
            x0 = box.left
            y0 = box.top
            x1 = x0 + box.width
            y1 = y0 + box.height
            draw.rectangle([x0, y0, x1, y1], fill=fill)

        return image, bboxes

    def redact(
        self,
        image: Image.Image,
        fill: Union[int, Tuple[int, int, int]] = (0, 0, 0),
        ocr_kwargs: Optional[dict] = None,
        ad_hoc_recognizers: Optional[List[PatternRecognizer]] = None,
        **text_analyzer_kwargs,
    ) -> Image.Image:
        """Redact method to redact the given image.

        Please notice, this method duplicates the image, creates a new instance and
        manipulate it.
        :param image: PIL Image to be processed.
        :param fill: colour to fill the shape - int (0-255) for
        grayscale or Tuple(R, G, B) for RGB.
        :param ocr_kwargs: Additional params for OCR methods.
        :param ad_hoc_recognizers: List of PatternRecognizer objects to use
        for ad-hoc recognizer.
        :param text_analyzer_kwargs: Additional values for the analyze method
        in AnalyzerEngine.

        :return: the redacted image
        """

        redacted_image, _ = self.redact_and_return_bbox(
            image=image,
            fill=fill,
            ocr_kwargs=ocr_kwargs,
            ad_hoc_recognizers=ad_hoc_recognizers,
            **text_analyzer_kwargs,
        )

        return redacted_image

    @staticmethod
    def _check_ad_hoc_recognizer_list(
        ad_hoc_recognizers: Optional[List[PatternRecognizer]] = None,
    ):
        """Check if the provided ad-hoc recognizer list is valid.

        :param ad_hoc_recognizers: List of PatternRecognizer objects to use
        for ad-hoc recognizer.
        """
        if isinstance(ad_hoc_recognizers, (list, type(None))):
            if isinstance(ad_hoc_recognizers, list):
                if len(ad_hoc_recognizers) >= 1:
                    are_recognizers = all(
                        isinstance(
                            x, presidio_analyzer.pattern_recognizer.PatternRecognizer
                        )
                        for x in ad_hoc_recognizers
                    )
                    if are_recognizers is False:
                        raise TypeError(
                            """All items in ad_hoc_recognizers list must be
                            PatternRecognizer objects"""
                        )
                else:
                    raise TypeError(
                        "ad_hoc_recognizers must be None or list of PatternRecognizer"
                    )
        else:
            raise TypeError(
                "ad_hoc_recognizers must be None or list of PatternRecognizer"
            )
