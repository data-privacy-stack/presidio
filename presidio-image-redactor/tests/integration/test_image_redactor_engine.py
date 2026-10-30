from typing import Callable

import pytest

from presidio_image_redactor import (
    ImageRedactorEngine,
    ImageAnalyzerEngine,
    DocumentIntelligenceOCR,
    OpenCVFaceRecognizer,
)

from tests.integration.methods import get_resource_image, compare_images, image_sim

from presidio_image_redactor.entities import ImageRecognizerResult

red_fill = (255, 0, 0)


def mock_tesseract_engine():
    """Get the Dicom Redactor Engine."""
    return ImageRedactorEngine()


def mock_di_engine():
    """Build the Dicom Redactor Engine with Document Intelligence OCR."""
    di_ocr = DocumentIntelligenceOCR()
    ia_engine = ImageAnalyzerEngine(ocr=di_ocr)
    return ImageRedactorEngine(image_analyzer_engine=ia_engine)


from tests.engine_test_utils import must_succeed, allow_failure


def all_engines_required():
    """Return all required engines and their must_pass flag for tests."""
    return [(must_succeed(mock_tesseract_engine)), (allow_failure(mock_di_engine))]


@pytest.mark.parametrize("engine_builder", all_engines_required())
def test_given_image_with_text_and_fill_then_text_is_greyed_out(engine_builder: Callable):
    # Image with PII entities
    image = get_resource_image("ocr_test.png")
    result_image = get_resource_image("ocr_test_redacted.png")
    redacted_image = engine_builder().redact(image, 1)
    assert compare_images(redacted_image, result_image)


@pytest.mark.parametrize("engine_builder", all_engines_required())
def test_given_image_with_text_and_matrix_fill_then_text_is_colored_out(engine_builder: Callable):
    # Image with PII entities
    image = get_resource_image("ocr_test.png")

    redacted_image = engine_builder().redact(image, red_fill)
    expected_result_image = get_resource_image("ocr_test_redacted_matrix.png")
    # The redacted image is closer to the expected result than the original image
    assert image_sim(redacted_image, expected_result_image) > image_sim(redacted_image, image)


@pytest.mark.parametrize("engine_builder", all_engines_required())
def test_given_image_without_text_and_fill_then_image_does_not_change(engine_builder: Callable):
    # Image without PII entities
    image = get_resource_image("no_ocr.jpg")
    redacted_image = engine_builder().redact(image, red_fill)
    assert compare_images(redacted_image, image)


@pytest.mark.parametrize("engine_builder", all_engines_required())
def test_given_two_word_entity_then_no_extra_bounding_box_appears(engine_builder: Callable):
    """Tests bounding boxes for multiword entities.

    Given a PII entity is identified,
    has two or more words,
    and second word is longer than first, then:
    no extra bounding box should be created.

    """

    # Image with two word PII entities
    image = get_resource_image("ocr_bounding_box.png")
    expected_image = get_resource_image("ocr_bounding_box_redacted.png")

    redacted_image = engine_builder().redact(image, red_fill)
    assert image_sim(expected_image, redacted_image) > 0.90


@pytest.mark.parametrize("engine_builder", all_engines_required())
def test_given_analzyer_kwargs_then_different_entities_are_redacted(engine_builder: Callable):
    """
    Tests that kwargs such as entities and score_threshold are available for
    redact method
    """
    # Image with PII entities
    image = get_resource_image("kwargs_test.jpg")
    redacted_image_no_args = engine_builder().redact(image)
    redacted_image_entities_args = ImageRedactorEngine().redact(image, entities=["PERSON", "LOCATION"])
    redacted_image_score_args = ImageRedactorEngine().redact(image, score_threshold=1)
    assert not compare_images(redacted_image_no_args, redacted_image_entities_args)
    assert not compare_images(redacted_image_no_args, redacted_image_score_args)
    assert not compare_images(redacted_image_entities_args, redacted_image_score_args)


@pytest.mark.parametrize("engine_builder", all_engines_required())
def test_redact_and_return_bbox_returns_same_image_as_redact(engine_builder: Callable):
    """Test that redact_and_return_bbox returns the same redacted image as redact."""
    
    image = get_resource_image("ocr_test.png")
    result_image = get_resource_image("ocr_test_redacted.png")
    
    engine = engine_builder()
    redacted_image_from_bbox, _ = engine.redact_and_return_bbox(image, 1)
    redacted_image_from_redact = engine.redact(image, 1)
    
    assert compare_images(redacted_image_from_bbox, result_image)
    assert compare_images(redacted_image_from_bbox, redacted_image_from_redact)


@pytest.mark.parametrize("engine_builder", all_engines_required())
def test_redact_and_return_bbox_returns_bboxes_for_image_with_text(engine_builder: Callable):
    """Test that redact_and_return_bbox returns non-empty bboxes for image with PII."""
    
    image = get_resource_image("ocr_test.png")
    
    engine = engine_builder()
    redacted_image, bboxes = engine.redact_and_return_bbox(image, 1)
    
    assert isinstance(bboxes, list)
    assert len(bboxes) > 0
    
    for bbox in bboxes:
        assert isinstance(bbox, ImageRecognizerResult)
        assert hasattr(bbox, 'left')
        assert hasattr(bbox, 'top')
        assert hasattr(bbox, 'width')
        assert hasattr(bbox, 'height')
        assert hasattr(bbox, 'entity_type')
        assert hasattr(bbox, 'score')
        assert isinstance(bbox.left, int)
        assert isinstance(bbox.top, int)
        assert isinstance(bbox.width, int)
        assert isinstance(bbox.height, int)
        assert bbox.width > 0
        assert bbox.height > 0


@pytest.mark.parametrize("engine_builder", all_engines_required())
def test_redact_and_return_bbox_returns_empty_bboxes_for_image_without_text(engine_builder: Callable):
    """Test that redact_and_return_bbox returns empty bboxes for image without PII."""
    
    image = get_resource_image("no_ocr.jpg")
    
    engine = engine_builder()
    redacted_image, bboxes = engine.redact_and_return_bbox(image, red_fill)
    
    assert isinstance(bboxes, list)
    assert len(bboxes) == 0


@pytest.mark.parametrize("engine_builder", all_engines_required())
def test_redact_and_return_bbox_with_matrix_fill(engine_builder: Callable):
    """Test redact_and_return_bbox with matrix fill color."""
    
    image = get_resource_image("ocr_test.png")
    expected_result_image = get_resource_image("ocr_test_redacted_matrix.png")
    
    engine = engine_builder()
    redacted_image, bboxes = engine.redact_and_return_bbox(image, red_fill)
    
    assert image_sim(redacted_image, expected_result_image) > image_sim(redacted_image, image)
    assert len(bboxes) > 0


@pytest.mark.parametrize("engine_builder", all_engines_required())
def test_redact_and_return_bbox_with_analyzer_kwargs(engine_builder: Callable):
    """Test that redact_and_return_bbox works with analyzer kwargs like entities and score_threshold."""
    
    image = get_resource_image("kwargs_test.jpg")
    
    engine = engine_builder()
    redacted_image_no_args, bboxes_no_args = engine.redact_and_return_bbox(image)
    redacted_image_entities, bboxes_entities = engine.redact_and_return_bbox(
        image, entities=["PERSON", "LOCATION"]
    )
    redacted_image_score, bboxes_score = engine.redact_and_return_bbox(
        image, score_threshold=1
    )
    
    assert not compare_images(redacted_image_no_args, redacted_image_entities)
    assert not compare_images(redacted_image_no_args, redacted_image_score)
    assert not compare_images(redacted_image_entities, redacted_image_score)
    
    assert len(bboxes_no_args) != len(bboxes_entities) or len(bboxes_no_args) != len(bboxes_score)


def test_given_visual_face_recognizer_then_face_region_is_redacted(synthetic_face_image):
    """A face is redacted even though the image contains no text at all."""
    engine = ImageRedactorEngine(ImageAnalyzerEngine(visual_recognizers=[OpenCVFaceRecognizer()]))

    redacted_image, bboxes = engine.redact_and_return_bbox(synthetic_face_image, red_fill)

    assert len(bboxes) == 1
    face = bboxes[0]
    assert face.entity_type == "FACE"
    center = (face.left + face.width // 2, face.top + face.height // 2)
    assert redacted_image.getpixel(center) == red_fill
