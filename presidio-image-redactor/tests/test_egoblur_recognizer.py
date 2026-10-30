import numpy as np
import pytest
from PIL import Image

torch = pytest.importorskip("torch")

from presidio_image_redactor import EgoBlurRecognizer  # noqa: E402
from presidio_image_redactor.entities import ImageRecognizerResult  # noqa: E402

# The stub emits these only when it is handed a uint8 BGR CHW tensor whose
# pixel (0, 0) is pure red, i.e. blue channel 0 and red channel 255.
BOXES = [
    [10.2, 20.4, 40.6, 60.8],  # kept
    [11.0, 21.0, 41.0, 61.0],  # suppressed by NMS (overlaps the first box)
    [100.0, 100.0, 140.0, 140.0],  # dropped by the score threshold
]
SCORES = [0.95, 0.93, 0.5]
EXPECTED_BBOX = (10, 20, 31, 41)
# float32 round trip, so the exact score must come from the tensor itself.
EXPECTED_SCORE = float(torch.tensor(SCORES)[0])


class _StubDetector(torch.nn.Module):
    """Minimal stand-in for a gen1 EgoBlur TorchScript detector.

    Boxes are emitted only for a uint8 BGR CHW tensor whose pixel (0, 0) is
    pure red, so a wrong rank or a wrong channel order yields no detections.
    """

    def __init__(self):
        super().__init__()
        self.boxes = torch.tensor(BOXES)
        self.labels = torch.ones(len(BOXES))
        self.scores = torch.tensor(SCORES)

    def forward(self, image):
        empty = torch.zeros((0, 4))
        no_detection = (empty, torch.zeros(0), torch.zeros(0), empty)
        if image.dim() != 3 or image.shape[0] != 3:
            return no_detection
        if int(image[2, 0, 0]) != 255 or int(image[0, 0, 0]) != 0:
            return no_detection
        return self.boxes, self.labels, self.scores, self.boxes


@pytest.fixture(scope="module")
def stub_model_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("egoblur") / "stub_detector.jit"
    torch.jit.script(_StubDetector()).save(str(path))
    return str(path)


@pytest.fixture
def red_pixel_image():
    """An RGB image whose top left pixel is pure red."""
    array = np.zeros((64, 64, 3), np.uint8)
    array[0, 0] = (255, 0, 0)
    return Image.fromarray(array)


def _expected(entity_type):
    return ImageRecognizerResult(
        entity_type, 0, 0, EXPECTED_SCORE, *EXPECTED_BBOX
    )


def test_given_face_model_only_then_face_entity_is_returned(
    stub_model_path, red_pixel_image
):
    recognizer = EgoBlurRecognizer(face_model_path=stub_model_path)

    assert recognizer.recognize(red_pixel_image) == [_expected("FACE")]


def test_given_lp_model_only_then_license_plate_entity_is_returned(
    stub_model_path, red_pixel_image
):
    recognizer = EgoBlurRecognizer(lp_model_path=stub_model_path)

    assert recognizer.recognize(red_pixel_image) == [_expected("LICENSE_PLATE")]


def test_given_both_models_then_face_results_precede_license_plates(
    stub_model_path, red_pixel_image
):
    recognizer = EgoBlurRecognizer(
        face_model_path=stub_model_path, lp_model_path=stub_model_path
    )

    assert recognizer.recognize(red_pixel_image) == [
        _expected("FACE"),
        _expected("LICENSE_PLATE"),
    ]


def test_given_pil_array_and_path_inputs_then_same_bbox_is_returned(
    stub_model_path, red_pixel_image, tmp_path
):
    recognizer = EgoBlurRecognizer(face_model_path=stub_model_path)
    image_path = tmp_path / "red_pixel.png"
    red_pixel_image.save(image_path)

    from_pil = recognizer.recognize(red_pixel_image)
    from_array = recognizer.recognize(np.array(red_pixel_image))
    from_path = recognizer.recognize(str(image_path))

    assert from_pil == [_expected("FACE")]
    assert from_array == from_pil
    assert from_path == from_pil


def test_given_rgba_array_then_alpha_is_dropped_and_bbox_is_returned(
    stub_model_path, red_pixel_image
):
    recognizer = EgoBlurRecognizer(face_model_path=stub_model_path)
    rgba_array = np.array(red_pixel_image.convert("RGBA"))

    assert recognizer.recognize(rgba_array) == [_expected("FACE")]


def test_given_greyscale_array_then_it_is_widened_to_three_channels(
    stub_model_path,
):
    recognizer = EgoBlurRecognizer(face_model_path=stub_model_path)
    greyscale_array = np.zeros((64, 64), np.uint8)

    assert recognizer._to_bgr(greyscale_array).shape == (64, 64, 3)
    assert recognizer.recognize(greyscale_array) == []


def test_given_no_model_path_then_value_error_is_raised():
    with pytest.raises(ValueError):
        EgoBlurRecognizer()


def test_given_out_of_range_threshold_then_value_error_is_raised(stub_model_path):
    with pytest.raises(ValueError):
        EgoBlurRecognizer(face_model_path=stub_model_path, face_score_threshold=5.0)


def test_given_unloadable_model_then_value_error_is_raised(tmp_path):
    not_a_model = tmp_path / "not_a_model.jit"
    not_a_model.write_text("definitely not torchscript")

    with pytest.raises(ValueError):
        EgoBlurRecognizer(face_model_path=str(not_a_model))


def test_given_non_uint8_array_then_value_error_is_raised(
    stub_model_path, red_pixel_image
):
    float_array = np.array(red_pixel_image).astype("float32")

    with pytest.raises(ValueError):
        EgoBlurRecognizer(face_model_path=stub_model_path).recognize(float_array)


def test_given_unsupported_input_type_then_value_error_is_raised(stub_model_path):
    with pytest.raises(ValueError):
        EgoBlurRecognizer(face_model_path=stub_model_path).recognize(42)
