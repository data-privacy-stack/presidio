import io
from typing import List, Optional

from PIL import Image, ImageChops
from presidio_analyzer import PatternRecognizer

from presidio_image_redactor.image_redactor_engine import ImageRedactorEngine


def fig2img(fig):
    """Convert a Matplotlib figure to a PIL Image and return it."""

    buf = io.BytesIO()
    fig.savefig(buf)
    buf.seek(0)
    img = Image.open(buf)
    return img


class ImagePiiVerifyEngine(ImageRedactorEngine):
    """ImagePiiVerifyEngine class only supporting Pii verification currently."""

    def verify(
        self,
        image: Image,
        is_greyscale: bool = False,
        display_image: bool = True,
        show_text_annotation: bool = True,
        ocr_kwargs: Optional[dict] = None,
        ad_hoc_recognizers: Optional[List[PatternRecognizer]] = None,
        **text_analyzer_kwargs,
    ) -> Image:
        """Annotate image with the detect PII entity.

        Please notice, this method duplicates the image, creates a
        new instance and manipulate it.

        :param image: PIL Image to be processed.
        :param is_greyscale: Whether the image is greyscale or not.
        :param display_image: If the verificationimage is displayed and returned.
        :param show_text_annotation: True to display entity type when displaying
        image with bounding boxes.
        :param ocr_kwargs: Additional params for OCR methods.
        :param ad_hoc_recognizers: List of PatternRecognizer objects to use
        for ad-hoc recognizer.
        :param text_analyzer_kwargs: Additional values for the analyze method
        in ImageAnalyzerEngine.

        :return: the annotated image
        """
        image = ImageChops.duplicate(image)

        # Check the ad-hoc recognizers list
        self._check_ad_hoc_recognizer_list(ad_hoc_recognizers)

        # Detect text
        perform_ocr_kwargs, ocr_threshold = (
            self.image_analyzer_engine._parse_ocr_kwargs(ocr_kwargs)
        )
        ocr_results = self.image_analyzer_engine.ocr.perform_ocr(
            image, **perform_ocr_kwargs
        )
        if ocr_threshold:
            ocr_results = self.image_analyzer_engine.threshold_ocr_result(
                ocr_results, ocr_threshold
            )
        ocr_bboxes = self.bbox_processor.get_bboxes_from_ocr_results(ocr_results)

        # Detect PII
        if ad_hoc_recognizers is None:
            analyzer_results = self.image_analyzer_engine.analyze(
                image,
                ocr_kwargs=ocr_kwargs,
                **text_analyzer_kwargs,
            )
        else:
            analyzer_results = self.image_analyzer_engine.analyze(
                image,
                ocr_kwargs=ocr_kwargs,
                ad_hoc_recognizers=ad_hoc_recognizers,
                **text_analyzer_kwargs,
            )
        analyzer_bboxes = self.bbox_processor.get_bboxes_from_analyzer_results(
            analyzer_results
        )

        # Prepare for plotting
        pii_bboxes = self.image_analyzer_engine.get_pii_bboxes(
            ocr_bboxes, analyzer_bboxes
        )
        if is_greyscale:
            use_greyscale_cmap = True
        else:
            use_greyscale_cmap = False

        # Get image with verification boxes
        verify_image = (
            self.image_analyzer_engine.add_custom_bboxes(
                image, pii_bboxes, show_text_annotation, use_greyscale_cmap
            )
            if display_image
            else None
        )

        return verify_image
