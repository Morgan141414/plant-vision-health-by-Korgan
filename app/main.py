from __future__ import annotations

import time
from pathlib import Path
from typing import Annotated

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import inference_backend, model_dir
from app.image_io import decode_image
from app.ml.classifier import PlantClassifier
from app.schemas import AnalysisResponse

PROJECT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_DIR / "static"

app = FastAPI(title="PlantVision AI", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

DISCLAIMER = (
    "Исследовательский демо-режим: результат не определяет вид, не диагностирует "
    "болезнь и не заменяет осмотр дендролога или фитопатолога."
)

classifier = PlantClassifier(
    model_path=model_dir() / "species.pt",
    labels_path=model_dir() / "species_labels.txt",
)


def vegetation_observation(image: np.ndarray) -> dict:
    """Return a reproducible visual observation, not a biological diagnosis."""
    blue, green, red = (image[:, :, channel].astype(np.int16) for channel in range(3))
    mask = (green > 45) & (green > red * 1.12) & (green > blue * 1.05)
    coverage = round(float(np.count_nonzero(mask)) / mask.size * 100, 2)
    rows, columns = np.where(mask)
    bbox = None if len(columns) == 0 else [
        int(columns.min()), int(rows.min()), int(columns.max() - columns.min() + 1), int(rows.max() - rows.min() + 1)
    ]
    return {"coverage_percent": coverage, "bbox": bbox}


def analyze_frame(frame: np.ndarray) -> dict:
    """Build one safe observation response for REST and streaming clients.

    The architecture deliberately keeps biological identification and health analysis
    unavailable until separately validated models are installed locally.
    """
    started = time.perf_counter()
    vegetation = vegetation_observation(frame)
    elapsed = round((time.perf_counter() - started) * 1000, 2)
    plant = classifier.classify(frame).to_dict()
    return {
        "mode": "demo_vegetation_mask",
        "plant": plant,
        "health": {"status": "REQUIRES_REVIEW", "confidence": None},
        "vegetation": vegetation,
        "frame": {"width": int(frame.shape[1]), "height": int(frame.shape[0])},
        "latency_ms": elapsed,
        "disclaimer": DISCLAIMER,
    }


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def healthcheck() -> dict:
    return {
        "service": "PlantVision AI",
        "status": "ok",
        "mode": "demo",
        "requested_backend": inference_backend(),
        "model_dir": str(model_dir()),
    }


@app.post("/api/v1/analyze", response_model=AnalysisResponse)
async def analyze(image: Annotated[UploadFile, File(...)]) -> AnalysisResponse:
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(415, "Поддерживаются JPEG, PNG и WEBP")
    content = await image.read()
    frame = decode_image(content)
    if frame is None:
        raise HTTPException(400, "Не удалось прочитать изображение")
    return AnalysisResponse.model_validate(analyze_frame(frame))


# Imported last because the router reuses the safe response contract above.
from app.stream import router as stream_router

app.include_router(stream_router)
