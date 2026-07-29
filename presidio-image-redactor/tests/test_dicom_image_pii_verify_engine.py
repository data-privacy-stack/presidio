"""Unit tests for dicom_image_pii_verify_engine"""

from copy import deepcopy
import pydicom

from presidio_image_redactor import (
    TesseractOCR,
    ImageAnalyzerEngine,
    DicomImagePiiVerifyEngine,
    BboxProcessor,
)
from typing import List
import pytest


@pytest.fixture(scope="module")
def mock_engine():
    """Instance of the DicomImagePiiVerifyEngine"""
    dicom_image_pii_verify_engine = DicomImagePiiVerifyEngine()

    return dicom_image_pii_verify_engine


@pytest.fixture(scope="module")
def mock_gt_single(get_mock_dicom_verify_results: dict):
    """Ground truth for a single instance"""
    gt = get_mock_dicom_verify_results["ground_truth"]
    return gt


# ------------------------------------------------------
# DicomImagePiiVerifyEngine.__init__()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "ocr_engine, image_analyzer_engine",
    [
        (TesseractOCR(), None),
        (None, ImageAnalyzerEngine()),
        (TesseractOCR(), ImageAnalyzerEngine()),
        (None, None),
    ],
)
def test_init_happy_path(ocr_engine: TesseractOCR, image_analyzer_engine: ImageAnalyzerEngine):
    """Test happy path for DicomImagePiiVerifyEngine.__init__
    Args:
        ocr_engine (TesseractOCR): Tesseract OCR engine or None.
        image_analyzer_engine (ImageAnalyzerEngine): Presidio image analyzer engine or None.
    """
    try:
        test_engine = DicomImagePiiVerifyEngine(ocr_engine, image_analyzer_engine)
    except Exception:
        raise TypeError("Invalid input into initializing")


# ------------------------------------------------------
# DicomImagePiiVerifyEngine.verify_dicom_instance()
# ------------------------------------------------------
def test_verify_dicom_instance_happy_path(
    mocker,
    mock_engine: DicomImagePiiVerifyEngine,
    get_mock_dicom_instance: pydicom.dataset.FileDataset,
):
    """Test happy path for DicomImagePiiVerifyEngine.verify_dicom_instance
    Args:
        mock_engine (DicomImagePiiVerifyEngine): Instantiated engine.
        get_mock_dicom_instance (pydicom.dataset.FileDataset): Loaded DICOM.
    """
    # Assign
    padding_width = 25

    mock_greyscale = mocker.patch.object(DicomImagePiiVerifyEngine, "_check_if_greyscale", return_value=None)
    mock_rescale_array = mocker.patch.object(DicomImagePiiVerifyEngine, "_rescale_dcm_pixel_array", return_value=None)
    mock_image_open = mocker.patch(
        "presidio_image_redactor.dicom_image_pii_verify_engine.Image.fromarray",
        return_value=None,
    )
    mock_add_padding = mocker.patch.object(DicomImagePiiVerifyEngine, "_add_padding", return_value=None)
    mock_parse_ocr_kwargs = mocker.patch.object(ImageAnalyzerEngine, "_parse_ocr_kwargs", return_value=[{}, None])
    mock_perform_ocr = mocker.patch.object(TesseractOCR, "perform_ocr", return_value=None)
    mock_format_ocr_results = mocker.patch.object(BboxProcessor, "get_bboxes_from_ocr_results", return_value=None)
    mock_analyze = mocker.patch.object(DicomImagePiiVerifyEngine, "_get_analyzer_results", return_value=None)
    mock_format_analyzer_results = mocker.patch.object(
        BboxProcessor, "get_bboxes_from_analyzer_results", return_value=None
    )
    mock_get_pii = mocker.patch.object(ImageAnalyzerEngine, "get_pii_bboxes", return_value=None)
    mock_add_bboxes = mocker.patch.object(ImageAnalyzerEngine, "add_custom_bboxes", return_value=None)

    # Act
    _, _, _ = mock_engine.verify_dicom_instance(get_mock_dicom_instance, padding_width)

    # Assert
    assert mock_greyscale.call_count == 1
    assert mock_rescale_array.call_count == 1
    assert mock_image_open.call_count == 1
    assert mock_add_padding.call_count == 1
    assert mock_parse_ocr_kwargs.call_count == 1
    assert mock_perform_ocr.call_count == 1
    assert mock_format_ocr_results.call_count == 1
    assert mock_analyze.call_count == 1
    assert mock_format_analyzer_results.call_count == 1
    assert mock_get_pii.call_count == 1
    assert mock_add_bboxes.call_count == 1


def test_verify_dicom_instance_exception(
    mock_engine: DicomImagePiiVerifyEngine,
    get_mock_dicom_instance: pydicom.dataset.FileDataset,
):
    """Test exceptions for DicomImagePiiVerifyEngine.verify_dicom_instance
    Args:
        mock_engine (DicomImagePiiVerifyEngine): Instantiated engine.
        get_mock_dicom_instance (pydicom.dataset.FileDataset): Loaded DICOM.
    """
    with pytest.raises(Exception) as exc_info:
        # Arrange
        padding_width = 25
        test_instance = deepcopy(get_mock_dicom_instance)
        del test_instance.PixelData
        expected_error_type = AttributeError

        # Act
        _, _, _ = mock_engine.verify_dicom_instance(test_instance, padding_width)

        # Assert
        assert expected_error_type == exc_info.typename


# ------------------------------------------------------
# DicomImagePiiVerifyEngine.eval_dicom_instance()
# ------------------------------------------------------
def test_eval_dicom_instance_happy_path(
    mocker,
    mock_engine: DicomImagePiiVerifyEngine,
    get_mock_dicom_instance: pydicom.dataset.FileDataset,
    mock_gt_single: dict,
):
    """Test happy path for DicomImagePiiVerifyEngine.eval_dicom_instance
    Args:
        mock_engine (DicomImagePiiVerifyEngine): Instantiated engine.
        get_mock_dicom_instance (pydicom.dataset.FileDataset): Loaded DICOM.
        mock_gt_single (dict): Ground truth for a single file.
    """
    # Assign
    padding_width = 25
    tolerance = 50

    mock_verify_instance = mocker.patch.object(
        DicomImagePiiVerifyEngine,
        "verify_dicom_instance",
        return_value=[None, None, None],
    )
    mock_remove_dups = mocker.patch.object(DicomImagePiiVerifyEngine, "_remove_duplicate_entities", return_value=None)
    mock_label_positives = mocker.patch.object(DicomImagePiiVerifyEngine, "_label_all_positives", return_value=None)
    mock_precision = mocker.patch.object(DicomImagePiiVerifyEngine, "calculate_precision", return_value=None)
    mock_recall = mocker.patch.object(DicomImagePiiVerifyEngine, "calculate_recall", return_value=None)

    # Act
    _, test_eval_results = mock_engine.eval_dicom_instance(
        get_mock_dicom_instance, mock_gt_single, padding_width, tolerance
    )

    # Assert
    assert type(test_eval_results) == dict
    assert mock_verify_instance.call_count == 1
    assert mock_remove_dups.call_count == 1
    assert mock_label_positives.call_count == 1
    assert mock_precision.call_count == 1
    assert mock_recall.call_count == 1


# ------------------------------------------------------
# DicomImagePiiVerifyEngine._remove_duplicate_entities()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "results, tolerance, expected_results",
    [
        (
            [
                {
                    "entity_type": "DATE_TIME",
                    "score": 0.6,
                    "left": 613,
                    "top": 26,
                    "width": 226,
                    "height": 35,
                },
                {
                    "entity_type": "PERSON",
                    "score": 1.0,
                    "left": 170,
                    "top": 72,
                    "width": 218,
                    "height": 35,
                },
                {
                    "entity_type": "PHONE_NUMBER",
                    "score": 0.4,
                    "left": 170,
                    "top": 72,
                    "width": 218,
                    "height": 35,
                },
            ],
            5,
            [
                {
                    "entity_type": "DATE_TIME",
                    "score": 0.6,
                    "left": 613,
                    "top": 26,
                    "width": 226,
                    "height": 35,
                },
                {
                    "entity_type": "PERSON",
                    "score": 1.0,
                    "left": 170,
                    "top": 72,
                    "width": 218,
                    "height": 35,
                },
            ],
        ),
        (
            [
                {
                    "entity_type": "DATE_TIME",
                    "score": 0.6,
                    "left": 613,
                    "top": 26,
                    "width": 226,
                    "height": 35,
                },
                {
                    "entity_type": "PERSON",
                    "score": 1.0,
                    "left": 170,
                    "top": 72,
                    "width": 218,
                    "height": 35,
                },
                {
                    "entity_type": "PHONE_NUMBER",
                    "score": 0.4,
                    "left": 170,
                    "top": 72,
                    "width": 218,
                    "height": 35,
                },
            ],
            999,
            [
                {
                    "entity_type": "PERSON",
                    "score": 1.0,
                    "left": 170,
                    "top": 72,
                    "width": 218,
                    "height": 35,
                }
            ],
        ),
        (
            [
                {
                    "entity_type": "DATE_TIME",
                    "score": 0.6,
                    "left": 123,
                    "top": 17,
                    "width": 100,
                    "height": 50,
                },
                {
                    "entity_type": "PERSON",
                    "score": 1.0,
                    "left": 127,
                    "top": 14,
                    "width": 98,
                    "height": 55,
                },
                {
                    "entity_type": "PHONE_NUMBER",
                    "score": 0.4,
                    "left": 999,
                    "top": 99,
                    "width": 199,
                    "height": 39,
                },
            ],
            5,
            [
                {
                    "entity_type": "PERSON",
                    "score": 1.0,
                    "left": 127,
                    "top": 14,
                    "width": 98,
                    "height": 55,
                },
                {
                    "entity_type": "PHONE_NUMBER",
                    "score": 0.4,
                    "left": 999,
                    "top": 99,
                    "width": 199,
                    "height": 39,
                },
            ],
        ),
        (
            [
                {
                    "entity_type": "DATE_TIME",
                    "score": 0.6,
                    "left": 123,
                    "top": 17,
                    "width": 100,
                    "height": 50,
                },
                {
                    "entity_type": "PERSON",
                    "score": 1.0,
                    "left": 127,
                    "top": 14,
                    "width": 98,
                    "height": 55,
                },
                {
                    "entity_type": "PHONE_NUMBER",
                    "score": 0.4,
                    "left": 999,
                    "top": 99,
                    "width": 199,
                    "height": 39,
                },
            ],
            0,
            [
                {
                    "entity_type": "DATE_TIME",
                    "score": 0.6,
                    "left": 123,
                    "top": 17,
                    "width": 100,
                    "height": 50,
                },
                {
                    "entity_type": "PERSON",
                    "score": 1.0,
                    "left": 127,
                    "top": 14,
                    "width": 98,
                    "height": 55,
                },
                {
                    "entity_type": "PHONE_NUMBER",
                    "score": 0.4,
                    "left": 999,
                    "top": 99,
                    "width": 199,
                    "height": 39,
                },
            ],
        ),
    ],
)
def test_remove_duplicate_entities_happy_path(
    mock_engine: DicomImagePiiVerifyEngine,
    results: list,
    tolerance: int,
    expected_results: list,
):
    """Test happy path for DicomImagePiiVerifyEngine._remove_duplicate_entities
    Args:
        mock_engine (DicomImagePiiVerifyEngine): Instantiated engine.
        results (list): Detected PHI dictionary.
        tolerance (int): Pixel difference tolerance for identifying dups.
        expected_results (list): Expected dictionary after removing dups.
    """
    # Act
    test_results_no_dups = mock_engine._remove_duplicate_entities(results, tolerance)

    # Assert
    assert sorted(map(lambda d: tuple(sorted(d.items())), test_results_no_dups)) == sorted(map(lambda d: tuple(sorted(d.items())), expected_results))


# ------------------------------------------------------
# DicomImagePiiVerifyEngine._label_all_positives()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "ocr_results, analyzer_results, tolerance, expected_results",
    [
        (
            None,
            None,
            50,
            [
                {
                    "label": "DAVIDSON",
                    "score": 1.0,
                    "left": 25,
                    "top": 25,
                    "width": 241,
                    "height": 37,
                },
                {
                    "label": "DOUGLAS",
                    "score": 0.85,
                    "left": 287,
                    "top": 25,
                    "width": 230,
                    "height": 36,
                },
                {
                    "label": "[M]",
                    "score": 1.0,
                    "left": 535,
                    "top": 25,
                    "width": 60,
                    "height": 45,
                },
                {
                    "label": "01.09.2012",
                    "score": 0.6,
                    "left": 613,
                    "top": 26,
                    "width": 226,
                    "height": 35,
                },
                {
                    "label": "06.16.1976",
                    "score": 0.4,
                    "left": 170,
                    "top": 72,
                    "width": 218,
                    "height": 35,
                },
            ],
        ),
        (
            None,
            [
                {
                    "entity_type": "PERSON",
                    "score": 1.0,
                    "left": 35,
                    "top": 30,
                    "width": 245,
                    "height": 39,
                },
                {
                    "entity_type": "PERSON",
                    "score": 1.0,
                    "left": 300,
                    "top": 15,
                    "width": 250,
                    "height": 40,
                },
                {
                    "entity_type": "PERSON",
                    "score": 1.0,
                    "left": 585,
                    "top": 25,
                    "width": 80,
                    "height": 45,
                },
            ],
            50,
            [
                {
                    "label": "DAVIDSON",
                    "score": 1.0,
                    "left": 25,
                    "top": 25,
                    "width": 241,
                    "height": 37,
                },
                {
                    "label": "DOUGLAS",
                    "score": 1.0,
                    "left": 287,
                    "top": 25,
                    "width": 230,
                    "height": 36,
                },
                {
                    "label": "[M]",
                    "score": 1.0,
                    "left": 535,
                    "top": 25,
                    "width": 60,
                    "height": 45,
                },
            ],
        ),
        (
            None,
            [
                {
                    "entity_type": "PERSON",
                    "score": 1.0,
                    "left": 99,
                    "top": 99,
                    "width": 99,
                    "height": 99,
                },
                {
                    "entity_type": "PERSON",
                    "score": 1.0,
                    "left": 199,
                    "top": 199,
                    "width": 199,
                    "height": 199,
                },
                {
                    "entity_type": "PERSON",
                    "score": 1.0,
                    "left": 535,
                    "top": 25,
                    "width": 60,
                    "height": 45,
                },
            ],
            10,
            [
                {
                    "label": "[M]",
                    "score": 1.0,
                    "left": 535,
                    "top": 25,
                    "width": 60,
                    "height": 45,
                }
            ],
        ),
    ],
)
def test_label_all_positives_happy_path(
    mock_engine: DicomImagePiiVerifyEngine,
    mock_gt_single: dict,
    get_mock_dicom_verify_results: dict,
    ocr_results: List[dict],
    analyzer_results: List[dict],
    tolerance: int,
    expected_results: List[dict],
):
    """Test happy path for DicomImagePiiVerifyEngine._label_all_positives

    Args:
        mock_engine (DicomImagePiiVerifyEngine): Instantiated engine.
        mock_gt_single (dict): Ground truth labels for single instance.
        get_mock_dicom_verify_results (dict): Dictionary containing results.
        ocr_results (dict): Formatted OCR results.
        analyzer_results (dict): Detected PHI dictionary.
        tolerance (int): Pixel difference tolerance for matching entities.
        expected_results (dict): Expected output dictionary.
    """
    # Assign
    if not ocr_results:
        ocr_results = get_mock_dicom_verify_results["ocr_results_formatted"]

    if not analyzer_results:
        analyzer_results = get_mock_dicom_verify_results["analyzer_results"]

    # Act
    test_all_pos = mock_engine._label_all_positives(mock_gt_single, ocr_results, analyzer_results, tolerance)

    # Assert
    assert sorted(map(lambda d: tuple(sorted(d.items())), test_all_pos)) == sorted(map(lambda d: tuple(sorted(d.items())), expected_results))


# ------------------------------------------------------
# DicomImagePiiVerifyEngine.calculate_precision()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "gt_labels, all_pos, expected_result",
    [
        (
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}, {"c": [7, 8, 9]}, {"d": [10, 11, 12]}],
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}, {"c": [7, 8, 9]}, {"d": [10, 11, 12]}],
            1.0,
        ),
        (
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}, {"c": [7, 8, 9]}, {"d": [10, 11, 12]}],
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}, {"c": [7, 8, 9]}],
            1.0,
        ),
        (
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}, {"c": [7, 8, 9]}, {"d": [10, 11, 12]}],
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}],
            1.0,
        ),
        (
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}, {"c": [7, 8, 9]}, {"d": [10, 11, 12]}],
            [{"a": [1, 2, 3]}],
            1.0,
        ),
        (
            [],
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}, {"c": [7, 8, 9]}, {"d": [10, 11, 12]}],
            0.0,
        ),
        (
            [{"a": [1, 2, 3]}],
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}, {"c": [7, 8, 9]}, {"d": [10, 11, 12]}],
            0.25,
        ),
        (
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}],
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}, {"c": [7, 8, 9]}, {"d": [10, 11, 12]}],
            0.5,
        ),
        (
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}, {"c": [7, 8, 9]}],
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}, {"c": [7, 8, 9]}, {"d": [10, 11, 12]}],
            0.75,
        ),
        (
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}, {"c": [7, 8, 9]}],
            [],
            0,
        ),
    ],
)
def test_calculate_precision_happy_path(
    mock_engine: DicomImagePiiVerifyEngine,
    gt_labels: List[dict],
    all_pos: List[dict],
    expected_result: float,
):
    """Test happy path for DicomImagePiiVerifyEngine.calculate_precision

    Args:
        mock_engine (DicomImagePiiVerifyEngine): Instantiated engine.
        gt_labels (dict): Ground truth labels for single instance.
        all_pos (dict): All positives (matched detected PHI).
        expected_result (float): Expected precision.
    """
    # Act
    test_precision = mock_engine.calculate_precision(gt_labels, all_pos)

    # Assert
    assert test_precision == expected_result


# ------------------------------------------------------
# DicomImagePiiVerifyEngine.calculate_recall()
# ------------------------------------------------------
@pytest.mark.parametrize(
    "gt_labels, all_pos, expected_result",
    [
        (
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}, {"c": [7, 8, 9]}, {"d": [10, 11, 12]}],
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}, {"c": [7, 8, 9]}, {"d": [10, 11, 12]}],
            1.0,
        ),
        (
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}, {"c": [7, 8, 9]}, {"d": [10, 11, 12]}],
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}, {"c": [7, 8, 9]}],
            0.75,
        ),
        (
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}, {"c": [7, 8, 9]}, {"d": [10, 11, 12]}],
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}],
            0.5,
        ),
        (
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}, {"c": [7, 8, 9]}, {"d": [10, 11, 12]}],
            [{"a": [1, 2, 3]}],
            0.25,
        ),
        (
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}, {"c": [7, 8, 9]}, {"d": [10, 11, 12]}],
            [{"a": [1, 2, 3]}, {"x": [99, 99, 99]}],
            0.25,
        ),
        (
            [],
            [{"a": [1, 2, 3]}, {"b": [4, 5, 6]}, {"c": [7, 8, 9]}],
            0,
        ),
    ],
)
def test_calculate_recall_happy_path(
    mock_engine: DicomImagePiiVerifyEngine,
    gt_labels: dict,
    all_pos: dict,
    expected_result: float,
):
    """Test happy path for DicomImagePiiVerifyEngine.calculate_recall

    Args:
        mock_engine (DicomImagePiiVerifyEngine): Instantiated engine.
        gt_labels (dict): Ground truth labels for single instance.
        all_pos (dict): All positives (matched detected PHI).
        expected_result (float): Expected precision.
    """
    # Act
    test_recall = mock_engine.calculate_recall(gt_labels, all_pos)

    # Assert
    assert test_recall == expected_result

def test_remove_duplicate_entities_keeps_highest_score():
    results = [
        {"entity_type": "DATE_TIME", "score": 0.4, "left": 10, "top": 10, "width": 100, "height": 30},
        {"entity_type": "PERSON",    "score": 1.0, "left": 10, "top": 10, "width": 100, "height": 30},
    ]
    
    deduped = DicomImagePiiVerifyEngine._remove_duplicate_entities(results, dup_pix_tolerance=5)
    assert len(deduped) == 1
    assert deduped[0]["entity_type"] == "PERSON"
