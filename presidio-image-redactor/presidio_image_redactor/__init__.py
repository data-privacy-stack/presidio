# isort: skip_file
"""Image Redactor root module."""

import logging

from .ocr import OCR
from .tesseract_ocr import TesseractOCR
from .document_intelligence_ocr import DocumentIntelligenceOCR
from .bbox import BboxProcessor
from .image_processing_engine import ImagePreprocessor
from .visual_object_recognizer import VisualObjectRecognizer
from .opencv_face_recognizer import OpenCVFaceRecognizer
from .image_analyzer_engine import ImageAnalyzerEngine
from .image_redactor_engine import ImageRedactorEngine
from .image_pii_verify_engine import ImagePiiVerifyEngine
from .dicom_image_redactor_engine import DicomImageRedactorEngine
from .dicom_image_pii_verify_engine import DicomImagePiiVerifyEngine
from .image_processing_engine import (
    ContrastSegmentedImageEnhancer,
    BilateralFilter,
    SegmentedAdaptiveThreshold,
    ImageRescaling,
)

# Set up default logging (with NullHandler)
logging.getLogger("presidio-image-redactor").addHandler(logging.NullHandler())

__all__ = [
    "OCR",
    "TesseractOCR",
    "DocumentIntelligenceOCR",
    "BboxProcessor",
    "VisualObjectRecognizer",
    "OpenCVFaceRecognizer",
    "ImageAnalyzerEngine",
    "ImageRedactorEngine",
    "ImagePreprocessor",
    "ImagePiiVerifyEngine",
    "DicomImageRedactorEngine",
    "DicomImagePiiVerifyEngine",
    "ContrastSegmentedImageEnhancer",
    "BilateralFilter",
    "SegmentedAdaptiveThreshold",
    "ImageRescaling",
]
