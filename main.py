"""HandGhost desktop entry point. Diagnostics do not require a graphical display."""

import argparse
import json
import platform
import sys


def main():
    parser = argparse.ArgumentParser(description="HandGhost — local hand tracking for your desktop")
    parser.add_argument("--config", help="Use a specific preferences JSON file")
    parser.add_argument(
        "--diagnostics", action="store_true", help="Print platform/camera capabilities and exit"
    )
    parser.add_argument(
        "--check-models",
        action="store_true",
        help="Load both bundled models and validate blank-frame inference",
    )
    parser.add_argument(
        "--check-gaze-model",
        choices=["l2cs", "gazetr", "itracker"],
        help="Run synthetic input through an installed optional gaze model",
    )
    parser.add_argument(
        "--model-directory", help="Parent directory containing optional gaze model folders"
    )
    args = parser.parse_args()
    from src.interaction.os_interaction import desktop_capability

    if args.diagnostics:
        from dataclasses import asdict

        from src.camera.camera_manager import CameraManager

        print(
            json.dumps(
                {
                    "platform": platform.platform(),
                    "python": platform.python_version(),
                    "desktop": asdict(desktop_capability()),
                    "camera_indices": CameraManager.list_available_cameras(),
                },
                indent=2,
            )
        )
        return 0
    if args.check_gaze_model:
        from src.eye.appearance_models import exercise_model
        from src.eye.model_registry import model_directory

        output = exercise_model(args.check_gaze_model, args.model_directory or model_directory())
        print(
            json.dumps(
                {
                    "model": args.check_gaze_model,
                    "synthetic_output": output,
                    "status": "inference passed; not an accuracy measurement",
                }
            )
        )
        return 0
    if args.check_models:
        import numpy as np

        from src.detection.hand_detector import HandDetector
        from src.eye.gaze_tracker import EyeTracker

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        detector = HandDetector()
        try:
            assert detector.detect(frame) == ([], []), "Unexpected hands in blank frame"
        finally:
            detector.close()
        eyes = EyeTracker()
        try:
            assert not eyes.detect(frame).face_present, "Unexpected face in blank frame"
        finally:
            eyes.close()
        print("PASS: bundled hand and eye models loaded and processed a blank frame")
        return 0
    from src.utils.settings_manager import SettingsManager

    try:
        from src.ui.app_ui import HandGhostGUI

        app = HandGhostGUI(SettingsManager(args.config))
    except Exception as exc:
        print(
            f"HandGhost could not open its window: {exc}\n"
            "Run in a graphical desktop session. See docs/README.md for Linux setup.",
            file=sys.stderr,
        )
        return 1
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
