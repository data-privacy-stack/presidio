import numpy as np
import pytest
from PIL import Image

from presidio_image_redactor import OpenCVFaceRecognizer


def test_given_synthetic_face_then_single_face_bbox_is_returned(synthetic_face_image):
    results = OpenCVFaceRecognizer().recognize(synthetic_face_image)

    assert len(results) == 1
    face = results[0]
    assert face.entity_type == "FACE"
    assert face.start == 0
    assert face.end == 0
    assert face.score == 0.85
    # The head is drawn centered, so the bbox must be inside the image and
    # roughly as large as the head (the image is 256x256).
    assert face.left > 0
    assert face.top > 0
    assert 150 <= face.width <= 240
    assert 150 <= face.height <= 240


def test_given_image_without_face_then_no_results_are_returned():
    blank_image = Image.fromarray(np.full((256, 256), 170, np.uint8)).convert("RGB")

    assert OpenCVFaceRecognizer().recognize(blank_image) == []


def test_given_different_input_types_then_same_face_bbox_is_returned(
    synthetic_face_image, tmp_path
):
    recognizer = OpenCVFaceRecognizer()
    image_path = tmp_path / "synthetic_face.png"
    synthetic_face_image.save(image_path)

    from_pil = recognizer.recognize(synthetic_face_image)
    from_array = recognizer.recognize(np.array(synthetic_face_image))
    from_path = recognizer.recognize(str(image_path))

    assert from_pil == from_array
    assert from_pil == from_path


def test_given_unsupported_input_type_then_value_error_is_raised():
    with pytest.raises(ValueError):
        OpenCVFaceRecognizer().recognize(42)


def test_given_invalid_cascade_path_then_value_error_is_raised(tmp_path):
    with pytest.raises(ValueError):
        OpenCVFaceRecognizer(cascade_path=str(tmp_path / "not_a_cascade.xml"))
