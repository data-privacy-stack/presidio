from typing import Optional, Tuple, Union

import cv2
import numpy as np
import PIL
from PIL import Image


class ImagePreprocessor:
    """ImagePreprocessor class.

    Parent class for image preprocessing objects.
    """

    def __init__(self, use_greyscale: bool = True) -> None:
        """Initialize the ImagePreprocessor class.

        :param use_greyscale: Whether to convert the image to greyscale.
        """
        self.use_greyscale = use_greyscale

    def preprocess_image(self, image: Image.Image) -> Tuple[Image.Image, dict]:
        """Preprocess the image to be analyzed.

        :param image: Loaded PIL image.

        :return: The processed image and any metadata regarding the
             preprocessing approach.
        """
        return image, {}

    def convert_image_to_array(self, image: Image.Image) -> np.ndarray:
        """Convert PIL image to numpy array.

        :param image: Loaded PIL image.

        :return: image pixels as a numpy array.

        """

        if isinstance(image, np.ndarray):
            img = image
        else:
            if self.use_greyscale:
                image = image.convert("L")
            img = np.asarray(image)
        return img

    @staticmethod
    def _get_bg_color(
        image: Image.Image, is_greyscale: bool, invert: bool = False
    ) -> Union[int, Tuple[int, int, int]]:
        """Select most common color as background color.

        :param image: Loaded PIL image.
        :param is_greyscale: Whether the image is greyscale.
        :param invert: TRUE if you want to get the inverse of the bg color.

        :return: Background color.
        """
        # Invert colors if invert flag is True
        if invert:
            if image.mode == "RGBA":
                # Handle transparency as needed
                r, g, b, a = image.split()
                rgb_image = Image.merge("RGB", (r, g, b))
                inverted_image = PIL.ImageOps.invert(rgb_image)
                r2, g2, b2 = inverted_image.split()

                image = Image.merge("RGBA", (r2, g2, b2, a))

            else:
                image = PIL.ImageOps.invert(image)

        # Get background color
        if is_greyscale:
            # Select most common color as color
            bg_color = int(np.bincount(image.flatten()).argmax())
        else:
            # Reduce size of image to 1 pixel to get dominant color
            tmp_image = image.copy()
            tmp_image = tmp_image.resize((1, 1), resample=0)
            bg_color = tmp_image.getpixel((0, 0))

        return bg_color

    @staticmethod
    def _get_image_contrast(image: np.ndarray) -> Tuple[float, float]:
        """Compute the contrast level and mean intensity of an image.

        :param image: Input image pixels (as a numpy array).

        :return: A tuple containing the contrast level and mean intensity of the image.
        """
        contrast = np.std(image)
        mean_intensity = np.mean(image)
        return contrast, mean_intensity


class BilateralFilter(ImagePreprocessor):
    """BilateralFilter class.

    The class applies bilateral filtering to an image. and returns the filtered
      image and metadata.
    """

    def __init__(
        self, diameter: int = 3, sigma_color: int = 40, sigma_space: int = 40
    ) -> None:
        """Initialize the BilateralFilter class.

        :param diameter: Diameter of each pixel neighborhood.
        :param sigma_color: value of sigma in the color space.
        :param sigma_space: value of sigma in the coordinate space.
        """
        super().__init__(use_greyscale=True)

        self.diameter = diameter
        self.sigma_color = sigma_color
        self.sigma_space = sigma_space

    def preprocess_image(self, image: Image.Image) -> Tuple[Image.Image, dict]:
        """Preprocess the image to be analyzed.

        :param image: Loaded PIL image.

        :return: The processed image and metadata (diameter, sigma_color, sigma_space).
        """
        image = self.convert_image_to_array(image)

        # Apply bilateral filtering
        filtered_image = cv2.bilateralFilter(
            image,
            self.diameter,
            self.sigma_color,
            self.sigma_space,
        )

        metadata = {
            "diameter": self.diameter,
            "sigma_color": self.sigma_color,
            "sigma_space": self.sigma_space,
        }

        return Image.fromarray(filtered_image), metadata


class SegmentedAdaptiveThreshold(ImagePreprocessor):
    """SegmentedAdaptiveThreshold class.

    The class applies adaptive thresholding to an image
    and returns the thresholded image and metadata.
    The parameters used to run the adaptivethresholding are selected based on
    the contrast level of the image.
    """

    def __init__(
        self,
        block_size: int = 5,
        contrast_threshold: int = 40,
        c_low_contrast: int = 10,
        c_high_contrast: int = 40,
        bg_threshold: int = 122,
    ) -> None:
        """Initialize the SegmentedAdaptiveThreshold class.

        :param block_size: Size of the neighborhood area for threshold calculation.
        :param contrast_threshold: Threshold for low contrast images.
        :param c_low_contrast: Constant added to the mean for low contrast images.
        :param c_high_contrast: Constant added to the mean for high contrast images.
        :param bg_threshold: Threshold for background color.
        """

        super().__init__(use_greyscale=True)
        self.block_size = block_size
        self.c_low_contrast = c_low_contrast
        self.c_high_contrast = c_high_contrast
        self.bg_threshold = bg_threshold
        self.contrast_threshold = contrast_threshold

    def preprocess_image(
        self, image: Union[Image.Image, np.ndarray]
    ) -> Tuple[Image.Image, dict]:
        """Preprocess the image.

        :param image: Loaded PIL image.

        :return: The processed image and metadata (C, background_color, contrast).
        """
        if not isinstance(image, np.ndarray):
            image = self.convert_image_to_array(image)

        # Determine background color
        background_color = self._get_bg_color(image, True)
        contrast, _ = self._get_image_contrast(image)

        c = (
            self.c_low_contrast
            if contrast <= self.contrast_threshold
            else self.c_high_contrast
        )

        if background_color < self.bg_threshold:
            adaptive_threshold_image = cv2.adaptiveThreshold(
                image,
                255,
                cv2.ADAPTIVE_THRESH_MEAN_C,
                cv2.THRESH_BINARY_INV,
                self.block_size,
                -c,
            )
        else:
            adaptive_threshold_image = cv2.adaptiveThreshold(
                image,
                255,
                cv2.ADAPTIVE_THRESH_MEAN_C,
                cv2.THRESH_BINARY,
                self.block_size,
                c,
            )

        metadata = {"C": c, "background_color": background_color, "contrast": contrast}
        return Image.fromarray(adaptive_threshold_image), metadata


class ImageRescaling(ImagePreprocessor):
    """ImageRescaling class. Rescales images based on their size."""

    def __init__(
        self,
        small_size: int = 1048576,
        large_size: int = 4000000,
        factor: int = 2,
        interpolation: int = cv2.INTER_AREA,
    ) -> None:
        """Initialize the ImageRescaling class.

        :param small_size: Threshold for small image size.
        :param large_size: Threshold for large image size.
        :param factor: Scaling factor for resizing.
        :param interpolation: Interpolation method for resizing.
        """
        super().__init__(use_greyscale=True)

        self.small_size = small_size
        self.large_size = large_size
        self.factor = factor
        self.interpolation = interpolation

    def preprocess_image(self, image: Image.Image) -> Tuple[Image.Image, dict]:
        """Preprocess the image to be analyzed.

        :param image: Loaded PIL image.

        :return: The processed image and metadata (scale_factor).
        """

        is_pil_image = isinstance(image, Image.Image)
        if not is_pil_image and not isinstance(image, np.ndarray):
            raise TypeError(
                "image must be a PIL Image or a NumPy array, "
                f"got {type(image).__name__}."
            )

        if is_pil_image:
            width, height = image.size
            pixel_count = width * height
        else:
            height, width = image.shape[:2]
            pixel_count = image.size

        scale_factor = 1
        if pixel_count < self.small_size:
            scale_factor = self.factor
        elif pixel_count > self.large_size:
            scale_factor = 1 / self.factor

        dimensions = (int(width * scale_factor), int(height * scale_factor))
        rescaled_image = (
            image.resize(dimensions)
            if is_pil_image
            else Image.fromarray(
                cv2.resize(image, dimensions, interpolation=self.interpolation)
            )
        )
        metadata = {"scale_factor": scale_factor}
        return rescaled_image, metadata


class ContrastSegmentedImageEnhancer(ImagePreprocessor):
    """Class containing all logic to perform contrastive segmentation.

    Contrastive segmentation is a preprocessing step that aims to enhance the
    text in an image by increasing the contrast between the text and the
    background. The parameters used to run the preprocessing are selected based
    on the contrast level of the image.
    """

    def __init__(
        self,
        bilateral_filter: Optional[BilateralFilter] = None,
        adaptive_threshold: Optional[SegmentedAdaptiveThreshold] = None,
        image_rescaling: Optional[ImageRescaling] = None,
        low_contrast_threshold: int = 40,
    ) -> None:
        """Initialize the class.

        :param bilateral_filter: Optional BilateralFilter instance.
        :param adaptive_threshold: Optional AdaptiveThreshold instance.
        :param image_rescaling: Optional ImageRescaling instance.
        :param low_contrast_threshold: Threshold for low contrast images.
        """

        super().__init__(use_greyscale=True)
        if not bilateral_filter:
            self.bilateral_filter = BilateralFilter()
        else:
            self.bilateral_filter = bilateral_filter

        if not adaptive_threshold:
            self.adaptive_threshold = SegmentedAdaptiveThreshold()
        else:
            self.adaptive_threshold = adaptive_threshold

        if not image_rescaling:
            self.image_rescaling = ImageRescaling()
        else:
            self.image_rescaling = image_rescaling

        self.low_contrast_threshold = low_contrast_threshold

    def preprocess_image(self, image: Image.Image) -> Tuple[Image.Image, dict]:
        """Preprocess the image to be analyzed.

        :param image: Loaded PIL image.

        :return: The processed image and metadata (background color, scale percentage,
             contrast level, and C value).
        """
        image = self.convert_image_to_array(image)

        # Apply bilateral filtering
        filtered_image, _ = self.bilateral_filter.preprocess_image(image)

        # Convert to grayscale
        pil_filtered_image = Image.fromarray(np.uint8(filtered_image))
        pil_grayscale_image = pil_filtered_image.convert("L")
        grayscale_image = np.asarray(pil_grayscale_image)

        # Improve contrast
        adjusted_image, _, adjusted_contrast = self._improve_contrast(grayscale_image)

        # Adaptive Thresholding
        adaptive_threshold_image, _ = self.adaptive_threshold.preprocess_image(
            adjusted_image
        )
        # Increase contrast
        _, threshold_image = cv2.threshold(
            np.asarray(adaptive_threshold_image),
            0,
            255,
            cv2.THRESH_BINARY | cv2.THRESH_OTSU,
        )

        # Rescale image
        rescaled_image, scale_metadata = self.image_rescaling.preprocess_image(
            threshold_image
        )

        return rescaled_image, scale_metadata

    def _improve_contrast(self, image: np.ndarray) -> Tuple[np.ndarray, str, str]:
        """Improve the contrast of an image based on its initial contrast level.

        :param image: Input image.

        :return: A tuple containing the improved image, the initial contrast level,
             and the adjusted contrast level.
        """
        contrast, mean_intensity = self._get_image_contrast(image)

        if contrast <= self.low_contrast_threshold:
            alpha = 1.5
            beta = -mean_intensity * alpha
            adjusted_image = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
            adjusted_contrast, _ = self._get_image_contrast(adjusted_image)
        else:
            adjusted_image = image
            adjusted_contrast = contrast
        return adjusted_image, contrast, adjusted_contrast
