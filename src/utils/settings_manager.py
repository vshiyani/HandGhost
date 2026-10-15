"""Validated, thread-safe preferences stored outside the application checkout."""

import copy
import json
import math
import os
import sys
import tempfile
from pathlib import Path
from threading import RLock

DEFAULTS = {
    "camera_index": 0,
    "camera_width": 640,
    "camera_height": 480,
    "target_fps": 30,
    "pinch_threshold": 30.0,
    "mouse_sensitivity": 2.5,
    "smoothing_factor": 0.45,
    "media_control_enabled": False,
    "controls_enabled": False,
    "mirror_camera": True,
    "tracking_mode": "hands",
    "dwell_click_enabled": False,
    "dwell_seconds": 1.2,
    "eye_calibration": None,
    "eye_model": "mediapipe",
    "model_directory": "",
    "eye_calibrations": {},
    "gestures": {
        "activate_movement": "right_hand_index_pinch",
        "left_click": "left_hand_index_pinch",
        "right_click": "left_hand_middle_pinch",
        "scroll": "right_hand_middle_pinch",
        "mute": "right_hand_fist",
    },
}
PRIMITIVES = ["None"] + [
    f"{hand}_hand_{pose}"
    for hand in ("left", "right")
    for pose in ("index_pinch", "middle_pinch", "fist")
]
ACTIONS = (
    "activate_movement",
    "left_click",
    "right_click",
    "scroll",
    "mute",
    "volume_up",
    "volume_down",
    "next_track",
    "prev_track",
)


def config_path():
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library/Application Support"
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "handghost/settings.json"


def validate(settings):
    result = copy.deepcopy(DEFAULTS)
    numeric = {
        "camera_index": (0, 99, int),
        "camera_width": (320, 1920, int),
        "camera_height": (240, 1080, int),
        "target_fps": (10, 60, int),
        "pinch_threshold": (10, 70, float),
        "mouse_sensitivity": (0.5, 8, float),
        "smoothing_factor": (0, 0.9, float),
        "dwell_seconds": (0.8, 3, float),
    }
    for key, (low, high, cast) in numeric.items():
        value = settings.get(key, result[key])
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
            result[key] = cast(max(low, min(high, value)))
    for key in (
        "media_control_enabled",
        "controls_enabled",
        "mirror_camera",
        "dwell_click_enabled",
    ):
        if isinstance(settings.get(key), bool):
            result[key] = settings[key]
    if settings.get("tracking_mode") in ("hands", "eyes"):
        result["tracking_mode"] = settings["tracking_mode"]
    if settings.get("eye_model") in ("mediapipe", "l2cs", "gazetr", "itracker"):
        result["eye_model"] = settings["eye_model"]
    if isinstance(settings.get("model_directory"), str):
        result["model_directory"] = settings["model_directory"]
    if isinstance(settings.get("eye_calibrations"), dict):
        result["eye_calibrations"] = copy.deepcopy(settings["eye_calibrations"])
    calibration = settings.get("eye_calibration")
    if isinstance(calibration, dict):
        # Numerical model validation is handled by GazeCalibration before use.
        result["eye_calibration"] = copy.deepcopy(calibration)
    mapping = settings.get("gestures", {})
    if isinstance(mapping, dict):
        for action in ACTIONS:
            if mapping.get(action) in PRIMITIVES:
                result["gestures"][action] = mapping[action]
    # Invalid or duplicate legacy mappings must never trigger multiple actions.
    used = set()
    for action, primitive in result["gestures"].items():
        if primitive != "None" and primitive in used:
            result["gestures"][action] = "None"
        elif primitive != "None":
            used.add(primitive)
    return result


class SettingsManager:
    def __init__(self, settings_file=None):
        self.settings_file = Path(settings_file) if settings_file else config_path()
        self._lock = RLock()
        self.settings = copy.deepcopy(DEFAULTS)
        self.load_settings()
        # Deliberately require opt-in each launch, even for previously saved settings.
        self.settings["controls_enabled"] = False
        self.settings["dwell_click_enabled"] = False

    def load_settings(self):
        try:
            with self.settings_file.open(encoding="utf-8") as stream:
                values = json.load(stream)
            if isinstance(values, dict):
                with self._lock:
                    self.settings = validate(values)
        except (OSError, ValueError, TypeError):
            pass  # Defaults remain usable; opening the app never writes preferences.

    def save_settings(self):
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        snapshot = self.snapshot()
        snapshot["controls_enabled"] = False
        snapshot["dwell_click_enabled"] = False
        name = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.settings_file.parent,
                prefix=".settings-",
                delete=False,
            ) as stream:
                name = stream.name
                json.dump(snapshot, stream, indent=2, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.settings_file)
        finally:
            if name and os.path.exists(name):
                os.unlink(name)

    def snapshot(self):
        with self._lock:
            return copy.deepcopy(self.settings)

    def get_setting(self, key):
        with self._lock:
            return copy.deepcopy(self.settings.get(key))

    def set_setting(self, key, value):
        with self._lock:
            updated = self.snapshot()
            updated[key] = value
            self.settings = validate(updated)
