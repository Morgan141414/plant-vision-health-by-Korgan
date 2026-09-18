from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import os


@lru_cache
def model_dir() -> Path:
    """Directory for local model artifacts. It is intentionally never downloaded at runtime."""
    return Path(os.getenv("PLANTVISION_MODEL_DIR", "models")).expanduser()


@lru_cache
def inference_backend() -> str:
    """Requested backend: demo, onnx or coreml. Unsupported values fall back safely."""
    requested = os.getenv("PLANTVISION_BACKEND", "demo").lower()
    return requested if requested in {"demo", "onnx", "coreml"} else "demo"
