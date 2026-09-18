import cv2
import numpy as np
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def jpeg_frame(frame: np.ndarray) -> bytes:
    ok, encoded = cv2.imencode(".jpg", frame)
    assert ok
    return encoded.tobytes()


def test_stream_returns_demo_contract_for_jpeg_frame():
    frame = np.zeros((30, 40, 3), dtype=np.uint8)
    frame[:, :20] = (0, 180, 0)

    with client.websocket_connect("/api/v1/stream") as websocket:
        websocket.send_bytes(jpeg_frame(frame))
        response = websocket.receive_json()

    assert response["mode"] == "demo_vegetation_mask"
    assert response["frame"] == {"width": 40, "height": 30}
    assert response["vegetation"]["coverage_percent"] > 40
    assert response["disclaimer"]


def test_stream_keeps_connection_after_invalid_payload():
    with client.websocket_connect("/api/v1/stream") as websocket:
        websocket.send_bytes(b"not-a-jpeg")
        error = websocket.receive_json()
        websocket.send_bytes(jpeg_frame(np.zeros((8, 8, 3), dtype=np.uint8)))
        response = websocket.receive_json()

    assert error["error"]["code"] == "INVALID_JPEG"
    assert response["frame"] == {"width": 8, "height": 8}
