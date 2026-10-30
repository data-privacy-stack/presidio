import math
import operator
import os
from functools import reduce

import numpy as np

from PIL import Image, ImageChops

IMAGE_SIMILARITY_PROPORTION = 0.95


def image_sim(image_one: Image, image_two: Image) -> float:
    # Compare if two images are similar, by thresholding
    delta = ImageChops.difference(image_one, image_two).convert("L")
    # Count number of black pixels, those that are exactly the same
    num_zero = (np.array(delta.get_flattened_data()) == 0).sum()
    num_nonzero = (np.array(delta.get_flattened_data()) != 0).sum()
    # If the number of black pixels is above a threshold, the images are not similar
    print(num_zero, num_nonzero, num_zero / (num_zero + num_nonzero))
    return num_zero / (num_zero + num_nonzero)


def compare_images(image_one: Image, image_two: Image) -> bool:
    return image_sim(image_one, image_two) >= IMAGE_SIMILARITY_PROPORTION


def get_resource_image(file_name: str) -> Image:
    script_dir = os.path.dirname(__file__)
    file_path = os.path.join(script_dir, "resources", file_name)
    return Image.open(file_path)
