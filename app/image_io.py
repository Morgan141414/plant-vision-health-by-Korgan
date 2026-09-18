from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image, UnidentifiedImageError


def decode_image(payload: bytes) -> np.ndarray | None:
    """Decode common image bytes to an OpenCV-compatible BGR array.

    Pillow keeps the lightweight demo runnable without installing OpenCV. Production
    ML adapters may still opt into OpenCV through the ``ml`` dependency extra.
    """
    try:
        with Image.open(BytesIO(payload)) as image:
            rgb = np.asarray(image.convert("RGB"))
    except (UnidentifiedImageError, OSError):
        return None
    return rgb[:, :, ::-1].copy()
