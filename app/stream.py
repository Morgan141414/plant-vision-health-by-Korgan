"""WebSocket transport for low-latency demo vegetation observations."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.image_io import decode_image
from app.main import analyze_frame
from app.schemas import AnalysisResponse

router = APIRouter()


def _error(code: str, message: str) -> dict:
    """Create a non-terminal protocol error response."""
    return {"error": {"code": code, "message": message}}


@router.websocket("/api/v1/stream")
async def stream_jpeg_frames(websocket: WebSocket) -> None:
    """Receive one JPEG frame per binary message and return one JSON result."""
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break

            payload = message.get("bytes")
            if payload is None:
                await websocket.send_json(
                    _error("UNSUPPORTED_FRAME", "Ожидается бинарный JPEG-кадр")
                )
                continue
            if not payload.startswith(b"\xff\xd8\xff"):
                await websocket.send_json(
                    _error("INVALID_JPEG", "Кадр должен быть в формате JPEG")
                )
                continue

            frame = decode_image(payload)
            if frame is None:
                await websocket.send_json(
                    _error("INVALID_JPEG", "Не удалось прочитать JPEG-кадр")
                )
                continue

            response = AnalysisResponse.model_validate(analyze_frame(frame))
            await websocket.send_json(response.model_dump(mode="json"))
    except WebSocketDisconnect:
        # A disconnected drone/client is a normal end of the stream.
        return
