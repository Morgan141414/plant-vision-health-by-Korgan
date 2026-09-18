from __future__ import annotations

import time
from typing import Annotated

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="PlantVision AI", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

DISCLAIMER = (
    "Исследовательский демо-режим: результат не определяет вид, не диагностирует "
    "болезнь и не заменяет осмотр дендролога или фитопатолога."
)


def vegetation_observation(image: np.ndarray) -> dict:
    """Return a reproducible visual observation, not a biological diagnosis."""
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([30, 30, 25]), np.array([95, 255, 255]))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    coverage = round(float(np.count_nonzero(mask)) / mask.size * 100, 2)
    points = cv2.findNonZero(mask)
    bbox = None if points is None else list(map(int, cv2.boundingRect(points)))
    return {"coverage_percent": coverage, "bbox": bbox}


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/health")
def healthcheck() -> dict:
    return {"service": "PlantVision AI", "status": "ok", "mode": "demo"}


@app.post("/api/v1/analyze")
async def analyze(image: Annotated[UploadFile, File(...)]) -> dict:
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(415, "Поддерживаются JPEG, PNG и WEBP")
    content = await image.read()
    frame = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(400, "Не удалось прочитать изображение")
    started = time.perf_counter()
    vegetation = vegetation_observation(frame)
    elapsed = round((time.perf_counter() - started) * 1000, 2)
    return {
        "mode": "demo_vegetation_mask",
        "plant": {"name": "unavailable", "confidence": None},
        "health": {"status": "REQUIRES_REVIEW", "confidence": None},
        "vegetation": vegetation,
        "frame": {"width": int(frame.shape[1]), "height": int(frame.shape[0])},
        "latency_ms": elapsed,
        "disclaimer": DISCLAIMER,
    }
