import numpy as np

from app.main import vegetation_observation


def test_green_pixels_are_observed():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    frame[:, :50] = (0, 180, 0)
    result = vegetation_observation(frame)
    assert result["coverage_percent"] > 45
    assert result["bbox"] == [0, 0, 50, 100]


def test_non_vegetation_has_no_bbox():
    frame = np.zeros((50, 50, 3), dtype=np.uint8)
    result = vegetation_observation(frame)
    assert result["coverage_percent"] == 0
    assert result["bbox"] is None
