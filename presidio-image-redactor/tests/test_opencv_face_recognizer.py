import numpy as np
import pytest
from PIL import Image

from presidio_image_redactor import OpenCVFaceRecognizer
from presidio_image_redactor.entities import ImageRecognizerResult


def test_given_synthetic_face_then_single_face_bbox_is_returned(synthetic_face_image):
    results = OpenCVFaceRecognizer().recognize(synthetic_face_image)

    assert len(results) == 1
    face = results[0]
    assert face.entity_type == "FACE"
    assert face.start == 0
    assert face.end == 0
    assert face.score == 0.85
    # Haar output for the committed synthetic face, with the opencv-python
    # version pinned in uv.lock. A change here means the cascade changed.
    assert (face.left, face.top, face.width, face.height) == (30, 28, 199, 199)


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


def test_given_detector_output_then_results_are_mapped_to_image_results(mocker):
    recognizer = OpenCVFaceRecognizer(score=0.5)
    # cv2.CascadeClassifier methods are read-only, so the whole classifier is
    # replaced rather than just detectMultiScale.
    classifier = mocker.patch.object(recognizer, "classifier")
    classifier.detectMultiScale.return_value = np.array(
        [[10, 20, 30, 40]], dtype=np.int32
    )

    assert recognizer.recognize(np.zeros((50, 50), np.uint8)) == [
        ImageRecognizerResult("FACE", 0, 0, 0.5, 10, 20, 30, 40)
    ]


def test_given_greyscale_array_then_same_face_bbox_is_returned(synthetic_face_image):
    recognizer = OpenCVFaceRecognizer()
    greyscale_array = np.array(synthetic_face_image.convert("L"))

    assert recognizer.recognize(greyscale_array) == recognizer.recognize(
        synthetic_face_image
    )


def test_given_non_uint8_array_then_value_error_is_raised(synthetic_face_image):
    float_array = np.array(synthetic_face_image).astype("float32")

    with pytest.raises(ValueError):
        OpenCVFaceRecognizer().recognize(float_array)


def test_given_out_of_range_score_then_value_error_is_raised():
    with pytest.raises(ValueError):
        OpenCVFaceRecognizer(score=5.0)
