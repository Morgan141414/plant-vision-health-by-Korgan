"""Local-only plant species classification adapter.

This module is a safe integration seam, not a claim that a general-purpose
image model can identify urban flora.  It never requests model weights from
the network: without a locally supplied, validated TorchScript model it
returns an explicit ``unavailable`` result.

The expected model is a TorchScript classifier receiving a float32 NCHW image
tensor (``1 x 3 x 224 x 224``) and returning one vector of logits.  Its class
order must exactly match the UTF-8 labels file supplied alongside it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

try:  # Keep the explicit fallback usable in a minimal Python environment.
    import cv2
except ImportError:  # pragma: no cover - OpenCV is a normal application dependency.
    cv2 = None


@dataclass(frozen=True)
class PlantClassification:
    """A classification response suitable for inclusion in the API contract."""

    name: str
    confidence: float | None
    mode: str
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PlantClassifier:
    """Run a locally stored TorchScript classifier when it is available.

    Args:
        model_path: Path to a locally exported ``.pt`` / TorchScript model.
        labels_path: UTF-8 text file with one label per line, in model order.
        device: ``"mps"``, ``"cpu"`` or ``"auto"``. ``auto`` selects MPS
            when PyTorch reports that it is usable, otherwise CPU.
        minimum_confidence: Predictions below this value are reported as
            unavailable. This makes low-certainty guesses impossible to mistake
            for an identification.

    No model is loaded until :meth:`classify` is called, allowing FastAPI to
    start normally on installations without optional ML dependencies.
    """

    def __init__(
        self,
        model_path: str | Path | None = None,
        labels_path: str | Path | None = None,
        *,
        device: str = "auto",
        minimum_confidence: float = 0.70,
    ) -> None:
        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be between 0 and 1")
        if device not in {"auto", "cpu", "mps"}:
            raise ValueError("device must be 'auto', 'cpu', or 'mps'")
        self.model_path = Path(model_path) if model_path else None
        self.labels_path = Path(labels_path) if labels_path else None
        self.device = device
        self.minimum_confidence = minimum_confidence
        self._model: Any | None = None
        self._torch: Any | None = None
        self._labels: list[str] | None = None
        self._unavailable_reason: str | None = None

    def classify(self, image_bgr: np.ndarray) -> PlantClassification:
        """Classify one OpenCV BGR image or return an honest fallback."""
        if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
            return self._unavailable("expected a BGR image with three channels")
        if not self._ensure_loaded():
            return self._unavailable(self._unavailable_reason or "model unavailable")

        try:
            tensor = self._preprocess(image_bgr)
            with self._torch.inference_mode():
                logits = self._model(tensor)
                if isinstance(logits, (tuple, list)):
                    logits = logits[0]
                probabilities = self._torch.softmax(logits, dim=1)[0]
                confidence, index = self._torch.max(probabilities, dim=0)
            confidence_value = float(confidence.detach().cpu().item())
            label_index = int(index.detach().cpu().item())
        except Exception as exc:  # Runtime errors must not become a plant label.
            return self._unavailable(f"inference failed: {type(exc).__name__}")

        if label_index >= len(self._labels):
            return self._unavailable("model output does not match labels file")
        if confidence_value < self.minimum_confidence:
            return self._unavailable(
                f"confidence {confidence_value:.2f} below threshold {self.minimum_confidence:.2f}"
            )
        return PlantClassification(
            name=self._labels[label_index],
            confidence=round(confidence_value, 4),
            mode="local_torchscript",
        )

    def _ensure_loaded(self) -> bool:
        if self._model is not None:
            return True
        if self._unavailable_reason is not None:
            return False
        if not self.model_path or not self.labels_path:
            self._unavailable_reason = "no local model and labels configured"
            return False
        if not self.model_path.is_file() or not self.labels_path.is_file():
            self._unavailable_reason = "local model or labels file not found"
            return False
        try:
            import torch
        except ImportError:
            self._unavailable_reason = "optional dependency PyTorch is not installed"
            return False
        try:
            labels = [line.strip() for line in self.labels_path.read_text("utf-8").splitlines()]
            if not labels or any(not label for label in labels):
                raise ValueError("labels must contain one non-empty label per line")
            requested_device = "mps" if self.device == "auto" and torch.backends.mps.is_available() else self.device
            if requested_device == "auto":
                requested_device = "cpu"
            if requested_device == "mps" and not torch.backends.mps.is_available():
                raise RuntimeError("MPS requested but unavailable")
            model = torch.jit.load(str(self.model_path), map_location=requested_device)
            model.eval()
            self._torch, self._model, self._labels = torch, model, labels
            self._device = requested_device
            return True
        except Exception as exc:
            self._unavailable_reason = f"could not load local model: {type(exc).__name__}"
            return False

    def _preprocess(self, image_bgr: np.ndarray) -> Any:
        # Resize and center-crop in the conventional ImageNet-compatible way.
        if cv2 is None:
            raise RuntimeError("OpenCV is not installed")
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        height, width = rgb.shape[:2]
        scale = 256 / min(height, width)
        resized = cv2.resize(rgb, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_LINEAR)
        top = (resized.shape[0] - 224) // 2
        left = (resized.shape[1] - 224) // 2
        crop = resized[top : top + 224, left : left + 224].astype(np.float32) / 255.0
        normalized = (crop - np.array([0.485, 0.456, 0.406], dtype=np.float32)) / np.array(
            [0.229, 0.224, 0.225], dtype=np.float32
        )
        return self._torch.from_numpy(normalized.transpose(2, 0, 1)).unsqueeze(0).to(self._device)

    def _unavailable(self, reason: str) -> PlantClassification:
        return PlantClassification(name="unavailable", confidence=None, mode="unavailable", reason=reason)
