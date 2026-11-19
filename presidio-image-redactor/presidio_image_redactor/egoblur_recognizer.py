import math
from typing import List, Optional

import cv2
import numpy as np
from PIL import Image

from presidio_image_redactor.entities import ImageRecognizerResult
from presidio_image_redactor.visual_object_recognizer import VisualObjectRecognizer

FACE_ENTITY = "FACE"
LICENSE_PLATE_ENTITY = "LICENSE_PLATE"

TORCH_IMPORT_ERROR = (
    "EgoBlurRecognizer requires torch and torchvision; "
    'install with pip install "presidio-image-redactor[egoblur]"'
)


class EgoBlurRecognizer(VisualObjectRecognizer):
    """Detect faces and license plates using Meta's EgoBlur models.

    EgoBlur (Raina et al., 2023, `arXiv:2308.13093 <https://arxiv.org/abs/2308.13093>`_)
    ships two detectors: a face detector and a license plate detector. Detected
    faces are returned as ``FACE`` entities and plates as ``LICENSE_PLATE``
    entities, both with ``start = end = 0``.

    The model weights are **not bundled** with Presidio and are never downloaded
    automatically. Download them yourself from
    https://www.projectaria.com/tools/egoblur/ (the EgoBlur license page states
    the Apache License 2.0) and pass the resulting file paths to this
    constructor.

    The model files are deserialised with ``torch.jit.load``, which executes
    the code stored in them: only load files from a source you trust, and
    verify the download. ``torch.jit.load`` is deprecated in recent torch
    releases and emits a ``FutureWarning``; the gen1 models are distributed
    as TorchScript only.

    Only the *gen1* TorchScript contract is supported: the detector is loaded
    with ``torch.jit.load`` and called with a single ``uint8`` BGR tensor in CHW
    layout (no batch dimension), returning the tuple
    ``(boxes, labels, scores, dims)`` where ``boxes`` are ``xyxy`` pixel
    coordinates. Any TorchScript model following that contract works. The gen2
    models are *not* supported: they require the detectron2 wrapper from the
    EgoBlur repository.

    Boxes are kept after class-agnostic NMS and a strictly-greater-than score
    threshold, as the EgoBlur reference script does. They are then clamped to
    the image and rounded outwards (floor/ceil) so a redaction covers the whole
    detected box; a box lying entirely outside the image is dropped.

    :param face_model_path: path to the TorchScript face detector. Omit it to
        detect license plates only.
    :param lp_model_path: path to the TorchScript license plate detector. Omit
        it to detect faces only.
    :param face_score_threshold: keep face detections scoring above this value.
    :param lp_score_threshold: keep plate detections scoring above this value.
    :param nms_iou_threshold: IoU threshold of the non-maximum suppression
        applied to each detector's boxes.
    :param device: torch device to run the models on. Defaults to ``"cuda"``
        when a CUDA device is available, otherwise ``"cpu"``.

    :raises ImportError: if torch or torchvision are not installed.
    :raises ValueError: if neither model path is given, if a threshold is
        outside the 0-1 range, or if a model cannot be loaded.
    """

    def __init__(
        self,
        face_model_path: Optional[str] = None,
        lp_model_path: Optional[str] = None,
        face_score_threshold: float = 0.9,
        lp_score_threshold: float = 0.9,
        nms_iou_threshold: float = 0.3,
        device: Optional[str] = None,
    ):
        try:
            import torch
            import torchvision
        except ImportError as error:
            raise ImportError(TORCH_IMPORT_ERROR) from error

        if not face_model_path and not lp_model_path:
            raise ValueError(
                "At least one of face_model_path and lp_model_path must be given"
            )
        for name, threshold in (
            ("face_score_threshold", face_score_threshold),
            ("lp_score_threshold", lp_score_threshold),
            ("nms_iou_threshold", nms_iou_threshold),
        ):
            if not 0 <= threshold <= 1:
                raise ValueError(f"{name} must be between 0 and 1")

        self._torch = torch
        self._nms = torchvision.ops.nms
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.nms_iou_threshold = nms_iou_threshold

        self.detectors = [
            (entity_type, self._load_model(path), threshold)
            for entity_type, path, threshold in (
                (FACE_ENTITY, face_model_path, face_score_threshold),
                (LICENSE_PLATE_ENTITY, lp_model_path, lp_score_threshold),
            )
            if path
        ]
        self.supported_entities = [entity_type for entity_type, _, _ in self.detectors]

    def _load_model(self, model_path: str):
        """Load a TorchScript detector onto the configured device.

        :param model_path: path to the TorchScript model file

        :return: the loaded model, in evaluation mode

        :raises ValueError: if the model cannot be loaded from model_path
        """
        try:
            model = self._torch.jit.load(model_path, map_location="cpu")
            return model.to(self.device).eval()
        except Exception as error:
            message = (
                f"Could not load an EgoBlur model from {model_path} "
                f"onto device {self.device}"
            )
            raise ValueError(message) from error

    def recognize(self, image: object) -> List[ImageRecognizerResult]:
        """Detect faces and license plates in a given image.

        Three channel arrays are interpreted as RGB; pass ``image[:, :, ::-1]``
        for the BGR output of ``cv2.imread``.

        :param image: PIL Image/numpy array or file path(str) to be processed

        :return: list of detected faces and license plates with image bounding
            boxes, faces first

        :raises ValueError: if image is not a PIL Image, a numpy array of a
            supported shape and dtype, or a file path.
        """
        bgr_image = self._to_bgr(image)
        height, width = bgr_image.shape[:2]
        tensor = self._torch.from_numpy(
            np.ascontiguousarray(bgr_image.transpose(2, 0, 1))
        ).to(self.device)

        results = []
        for entity_type, detector, threshold in self.detectors:
            for box, score in self._detect(detector, tensor, threshold):
                left = max(0, math.floor(box[0]))
                top = max(0, math.floor(box[1]))
                right = min(width, math.ceil(box[2]))
                bottom = min(height, math.ceil(box[3]))
                if right <= left or bottom <= top:
                    continue
                results.append(
                    ImageRecognizerResult(
                        entity_type,
                        0,
                        0,
                        score,
                        left,
                        top,
                        right - left,
                        bottom - top,
                    )
                )
        return results

    def _detect(self, detector, tensor, threshold: float) -> List[tuple]:
        """Run one detector and keep the suppressed, above-threshold boxes.

        :param detector: a gen1 TorchScript EgoBlur detector
        :param tensor: the uint8 BGR CHW image tensor
        :param threshold: keep detections scoring above this value

        :return: list of (xyxy box, score) tuples
        """
        with self._torch.no_grad():
            # A gen1 detector may write into its input, as the EgoBlur reference
            # script's image_tensor.clone() implies; give each one its own copy.
            boxes, _, scores, _ = detector(tensor.clone())
        keep = self._nms(boxes, scores, self.nms_iou_threshold)
        boxes, scores = boxes[keep], scores[keep]
        above = scores > threshold
        return [
            (box.tolist(), float(score))
            for box, score in zip(boxes[above], scores[above])
        ]

    @staticmethod
    def _to_bgr(image: object) -> np.ndarray:
        """Convert the supported image types to a uint8 BGR numpy array.

        :param image: PIL Image/numpy array or file path(str) to be converted

        :return: the image as a HxWx3 uint8 BGR numpy array
        """
        if isinstance(image, str):
            try:
                with Image.open(image) as opened_image:
                    return np.array(opened_image.convert("RGB"))[:, :, ::-1]
            except (OSError, ValueError) as error:
                raise ValueError(f"Could not read an image from {image}") from error

        if isinstance(image, Image.Image):
            return np.array(image.convert("RGB"))[:, :, ::-1]

        if isinstance(image, np.ndarray):
            if image.ndim in (2, 3) and image.dtype != np.uint8:
                raise ValueError(f"image array must be uint8, got {image.dtype}")
            if image.ndim == 2:
                return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            if image.ndim == 3 and image.shape[2] == 1:
                return cv2.cvtColor(image[:, :, 0], cv2.COLOR_GRAY2BGR)
            if image.ndim == 3 and image.shape[2] in (3, 4):
                return image[:, :, :3][:, :, ::-1]

        raise ValueError(
            "image must be a PIL Image, a 2D or 3D numpy array or a file path"
        )
