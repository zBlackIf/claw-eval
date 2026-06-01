"""Image utility operations for the annotation tool."""
from pathlib import Path
import numpy as np


def normalize_path_list(paths: list[str]) -> list[Path]:
    """Normalize a list of path strings to Path objects, removing prefixes."""
    result = []
    for p in paths:
        # Remove common prefixes
        cleaned = p.removeprefix("file://")
        cleaned = cleaned.removeprefix("./")
        result.append(Path(cleaned))
    return result


def batch_resize_images(
    images: list[np.ndarray],
    target_sizes: list[tuple[int, int]],
) -> list[np.ndarray]:
    """Resize a batch of images to target sizes.

    Args:
        images: List of input images as numpy arrays
        target_sizes: List of (width, height) tuples, one per image

    Returns:
        List of resized images

    Raises:
        ValueError: If images and target_sizes have different lengths
    """
    import cv2

    # Validate inputs match
    for img, size in zip(images, target_sizes, strict=True):
        pass  # zip with strict validates length match

    results = []
    for img, (w, h) in zip(images, target_sizes, strict=True):
        resized = cv2.resize(img, (w, h), interpolation=cv2.INTER_LINEAR)
        results.append(resized)
    return results


def compute_histogram(image: np.ndarray, channel: int = 0) -> np.ndarray:
    """Compute histogram for a single channel of an image."""
    import cv2
    hist = cv2.calcHist([image], [channel], None, [256], [0, 256])
    return hist.flatten()


def apply_clahe(
    image: np.ndarray,
    clip_limit: float = 2.0,
    tile_grid_size: tuple[int, int] = (8, 8),
) -> np.ndarray:
    """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization).

    Enhances contrast in annotation images for better visibility of
    traffic lights in low-light conditions.
    """
    import cv2

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    enhanced_l = clahe.apply(l_channel)

    enhanced_lab = cv2.merge((enhanced_l, a_channel, b_channel))
    return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)


def detect_overexposed_regions(
    image: np.ndarray,
    threshold: int = 250,
) -> list[tuple[int, int, int, int]]:
    """Detect overexposed (blown-out) regions that may hide traffic lights.

    Returns bounding boxes of overexposed patches.
    """
    import cv2

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    regions = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w * h > 100:  # Filter tiny noise
            regions.append((x, y, w, h))
    return regions
