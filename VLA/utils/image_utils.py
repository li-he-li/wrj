"""
Image utilities for VLA system.

Handles image encoding/decoding for VLM input.
"""

import base64
import io
from typing import Union
import numpy as np
from PIL import Image


def encode_image_to_base64(image: np.ndarray, format: str = "JPEG") -> str:
    """
    Encode numpy image array to base64 string.

    Args:
        image: RGB image as numpy array (H, W, C)
        format: Image format (JPEG, PNG)

    Returns:
        Base64 encoded string

    Raises:
        ValueError: If image is invalid
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid image: empty or None")

    # Ensure RGB format
    if len(image.shape) == 2:
        image = np.stack([image] * 3, axis=-1)
    elif image.shape[2] == 4:
        image = image[:, :, :3]  # Remove alpha channel

    # Convert numpy array to PIL Image
    pil_image = Image.fromarray(image.astype('uint8'))

    # Save to bytes buffer
    buffer = io.BytesIO()
    pil_image.save(buffer, format=format)
    buffer.seek(0)

    # Encode to base64
    base64_string = base64.b64encode(buffer.read()).decode('utf-8')

    return base64_string


def create_image_url(base64_image: str, mime_type: str = "image/jpeg") -> str:
    """
    Create data URL from base64 image string.

    Args:
        base64_image: Base64 encoded image
        mime_type: MIME type (image/jpeg, image/png)

    Returns:
        Data URL string (e.g., "data:image/jpeg;base64,...")
    """
    return f"data:{mime_type};base64,{base64_image}"


def decode_base64_to_image(base64_string: str) -> np.ndarray:
    """
    Decode base64 string to numpy array.

    Args:
        base64_string: Base64 encoded image

    Returns:
        RGB image as numpy array

    Raises:
        ValueError: If base64 string is invalid
    """
    try:
        # Decode base64
        image_data = base64.b64decode(base64_string)

        # Convert to PIL Image
        pil_image = Image.open(io.BytesIO(image_data))

        # Convert to RGB if needed
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')

        # Convert to numpy array
        image_array = np.array(pil_image)

        return image_array

    except Exception as e:
        raise ValueError(f"Failed to decode base64 image: {e}")


def resize_image(
    image: np.ndarray,
    max_width: int = 1280,
    max_height: int = 720
) -> np.ndarray:
    """
    Resize image while maintaining aspect ratio.

    Args:
        image: Input image
        max_width: Maximum width
        max_height: Maximum height

    Returns:
        Resized image
    """
    h, w = image.shape[:2]

    # Calculate scaling factor
    scale = min(max_width / w, max_height / h)

    # Don't upscale
    if scale >= 1:
        return image

    # Resize
    pil_image = Image.fromarray(image.astype('uint8'))
    new_size = (int(w * scale), int(h * scale))
    resized = pil_image.resize(new_size, Image.LANCZOS)

    return np.array(resized)
