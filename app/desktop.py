"""Local real-time camera application for PlantVision AI.

Run ``plantvision-camera`` after installing the project. The program has no
browser UI and never asks the operator to upload a photo. It reads frames from
the selected local camera and renders observations over the live preview.
"""

from __future__ import annotations

import argparse
import sys

try:
    import cv2
except ImportError as error:  # pragma: no cover - environment-specific dependency.
    raise SystemExit(
        "Для работы с камерой установите зависимости: pip install -e '.[camera]'"
    ) from error

from app.main import analyze_frame


def _draw_panel(frame, observation: dict) -> None:
    """Render the real observation status without inventing ML predictions."""
    height, width = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (min(width, 610), 170), (12, 28, 18), -1)
    cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)

    vegetation = observation["vegetation"]
    bbox = vegetation["bbox"]
    if bbox:
        x, y, box_width, box_height = bbox
        cv2.rectangle(frame, (x, y), (x + box_width, y + box_height), (104, 220, 100), 2)

    plant = observation["plant"]
    species_text = "Вид: модель не подключена" if plant["name"] == "unavailable" else f"Вид: {plant['name']}"
    lines = [
        "PlantVision AI | LIVE CAMERA",
        f"Растительный покров: {vegetation['coverage_percent']:.1f}%",
        species_text,
        "Состояние: требуется экспертная модель",
        "Q / ESC: выход",
    ]
    for index, text in enumerate(lines):
        color = (115, 235, 120) if index in {0, 1} else (230, 235, 230)
        cv2.putText(frame, text, (18, 31 + index * 29), cv2.FONT_HERSHEY_SIMPLEX, 0.62, color, 2, cv2.LINE_AA)


def run_camera(camera_index: int = 0, width: int = 1280, height: int = 720) -> None:
    capture = cv2.VideoCapture(camera_index)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    if not capture.isOpened():
        raise RuntimeError(
            f"Не удалось открыть камеру {camera_index}. Проверьте разрешение Camera для Terminal и номер камеры."
        )

    window_name = "PlantVision AI - локальная камера"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError("Камера перестала передавать кадры")
            frame = cv2.flip(frame, 1)
            observation = analyze_frame(frame)
            _draw_panel(frame, observation)
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
