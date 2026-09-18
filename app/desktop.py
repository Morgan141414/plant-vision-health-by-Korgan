"""Local real-time camera application for PlantVision AI.

Run ``plantvision-camera`` after installing the project. The program has no
browser UI and never asks the operator to upload a photo. It reads frames from
the selected local camera and renders observations over the live preview.
"""

from __future__ import annotations

import argparse
from functools import lru_cache
import platform
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    import cv2
except ImportError as error:  # pragma: no cover - environment-specific dependency.
    raise SystemExit(
        "Для работы с камерой установите зависимости: pip install -e '.[camera]'"
    ) from error

from app.main import analyze_frame


FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"


@lru_cache
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Use a macOS font with Cyrillic glyphs instead of OpenCV's ASCII font."""
    path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else FONT_PATH
    try:
        return ImageFont.truetype(path, size)
    except OSError:  # Portable fallback for non-macOS development machines.
        return ImageFont.load_default()


def _text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, font: ImageFont.ImageFont, fill: tuple[int, int, int, int]) -> None:
    draw.text(xy, value, font=font, fill=fill)


def _draw_panel(frame: np.ndarray, observation: dict) -> np.ndarray:
    """Render a polished Cyrillic overlay without inventing ML predictions."""
    height, width = frame.shape[:2]
    vegetation = observation["vegetation"]
    bbox = vegetation["bbox"]
    if bbox:
        x, y, box_width, box_height = bbox
        cv2.rectangle(frame, (x, y), (x + box_width, y + box_height), (90, 232, 132), 3)

    canvas = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA))
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    panel_width = min(width - 32, 550)
    panel_height = 214
    panel = (18, 18, panel_width + 18, panel_height + 18)
    draw.rounded_rectangle(panel, radius=18, fill=(12, 27, 20, 224), outline=(98, 217, 126, 150), width=1)
    draw.rounded_rectangle((36, 38, 168, 68), radius=15, fill=(61, 139, 78, 255))

    _text(draw, (49, 45), "LIVE CAMERA", _font(15, True), (237, 255, 238, 255))
    _text(draw, (38, 86), "PlantVision AI", _font(29, True), (242, 250, 244, 255))
    _text(draw, (38, 126), f"Растительный покров  {vegetation['coverage_percent']:.1f}%", _font(20, True), (126, 234, 147, 255))

    plant = observation["plant"]
    species_text = "Вид: ожидание модели" if plant["name"] == "unavailable" else f"Вид: {plant['name']}"
    _text(draw, (38, 160), species_text, _font(17), (230, 238, 231, 255))
    _text(draw, (38, 189), "Состояние: требуется проверенная модель", _font(15), (183, 200, 187, 255))
    _text(draw, (width - 146, height - 37), "Q / Esc  Выход", _font(14), (240, 246, 240, 230))

    composed = Image.alpha_composite(canvas, overlay).convert("RGB")
    return cv2.cvtColor(np.asarray(composed), cv2.COLOR_RGB2BGR)


def run_camera(camera_index: int = 0, width: int = 1280, height: int = 720) -> None:
    backend = cv2.CAP_AVFOUNDATION if platform.system() == "Darwin" else cv2.CAP_ANY
    capture = cv2.VideoCapture(camera_index, backend)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if not capture.isOpened():
        raise RuntimeError(
            f"Не удалось открыть камеру {camera_index}. В macOS откройте System Settings > "
            "Privacy & Security > Camera и разрешите доступ Terminal или VS Code, затем полностью "
            "перезапустите это приложение. Также проверьте номер камеры через --camera 1."
        )

    window_name = "PlantVision AI - Live Camera"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError("Камера перестала передавать кадры")
            frame = cv2.flip(frame, 1)
            observation = analyze_frame(frame)
            frame = _draw_panel(frame, observation)
            cv2.imshow(window_name, frame)
            key = cv2.waitKey(1) & 0xFF
            if key in {27, ord("q"), ord("Q")}:
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()


def main() -> None:
    parser = argparse.ArgumentParser(description="PlantVision AI local camera application")
    parser.add_argument("--camera", type=int, default=0, help="Camera index, default: 0")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    args = parser.parse_args()
    try:
        run_camera(args.camera, args.width, args.height)
    except RuntimeError as error:
        print(f"Ошибка камеры: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
