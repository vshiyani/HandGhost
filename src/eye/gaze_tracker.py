"""Iris-based gaze approximation, calibrated locally for one camera/screen setup.

This is a webcam estimate, not a replacement for dedicated eye-tracking hardware.
No images are retained. Calibration stores only regression coefficients.
"""

import math
import time
from dataclasses import dataclass

import cv2
import numpy as np

from src.gesture.gesture_recognizer import Gesture


@dataclass
class EyeObservation:
    features: object = None
    eyes_open: bool = False
    face_present: bool = False


class GazeCalibration:
    VERSION = 1

    def __init__(self, data):
        if not isinstance(data, dict) or data.get("version") != self.VERSION:
            raise ValueError("Calibrate eye tracking first.")
        try:
            self.mean = np.asarray(data["mean"], dtype=float)
            self.scale = np.asarray(data["scale"], dtype=float)
            self.weights = np.asarray(data["weights"], dtype=float)
            self.screen = tuple(data["screen"])
            self.error = float(data["error"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid eye calibration. Please recalibrate.") from exc
        if (
            self.mean.shape != (4,)
            or self.scale.shape != (4,)
            or self.weights.shape != (5, 2)
            or not all(np.isfinite(array).all() for array in (self.mean, self.scale, self.weights))
            or np.any(self.scale <= 0)
            or len(self.screen) != 2
            or any(
                not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0
                for value in self.screen
            )
            or not math.isfinite(self.error)
        ):
            raise ValueError("Invalid eye calibration. Please recalibrate.")

    @classmethod
    def fit(cls, features, targets, screen):
        features, targets = np.asarray(features, dtype=float), np.asarray(targets, dtype=float)
        if features.shape != (9, 4) or targets.shape != (9, 2) or not np.isfinite(features).all():
            raise ValueError("Collect all nine calibration points with your eyes visible.")
        mean, scale = features.mean(axis=0), features.std(axis=0)
        if scale[0] < 0.008 or scale[1] < 0.008:
            raise ValueError(
                "Too little eye movement was detected. Improve lighting and try again."
            )
        scale = np.maximum(scale, 0.01)
        design = np.column_stack((np.ones(9), (features - mean) / scale))
        penalty = np.diag([0, 0.25, 0.25, 0.6, 0.6])
        weights = np.linalg.solve(design.T @ design + penalty, design.T @ targets)
        # Leave-one-target-out error exposes a poor fit better than training error.
        errors = []
        for index in range(9):
            train = np.arange(9) != index
            fitted = np.linalg.solve(
                design[train].T @ design[train] + penalty, design[train].T @ targets[train]
            )
            errors.append(np.linalg.norm(design[index] @ fitted - targets[index]))
        error = float(np.mean(errors))
        if error > 0.24:
            raise ValueError(
                "Calibration was inconsistent. Keep your head still and look at each dot before pressing Space."
            )
        return {
            "version": cls.VERSION,
            "mean": mean.tolist(),
            "scale": scale.tolist(),
            "weights": weights.tolist(),
            "screen": list(screen),
            "error": error,
        }

    def predict(self, features):
        features = np.asarray(features, dtype=float)
        if features.shape != (4,) or not np.isfinite(features).all():
            return None
        normalized = (features - self.mean) / self.scale
        # Refuse a pose far outside the calibrated range instead of extrapolating wildly.
        if np.max(np.abs(normalized[:2])) > 5 or np.max(np.abs(normalized[2:])) > 8:
            return None
        position = np.r_[1, normalized] @ self.weights
        return tuple(np.clip(position, 0.015, 0.985))


class EyeTracker:
    def __init__(self, backend=None):
        self.backend = backend
        self.input_mirrored = False
        import mediapipe as mp

        self.model = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.65,
            min_tracking_confidence=0.65,
        )

    @staticmethod
    def extract(points, width, height):
        # Work in pixels so aspect ratio does not distort eye shape or closure detection.
        xy = np.array([(point.x * width, point.y * height) for point in points])
        values = []
        openness = []
        for outer, inner, iris, top, bottom in (
            (33, 133, 468, 159, 145),
            (362, 263, 473, 386, 374),
        ):
            a, b = xy[outer], xy[inner]
            # Both eye axes must point in the same image direction.
            if a[0] > b[0]:
                a, b = b, a
            axis = b - a
            eye_width = np.linalg.norm(axis)
            if eye_width < 8:
                return EyeObservation(face_present=True)
            horizontal = axis / eye_width
            vertical = np.array([-horizontal[1], horizontal[0]])
            offset = xy[iris] - (a + b) / 2
            values.append(
                (np.dot(offset, horizontal) / eye_width, np.dot(offset, vertical) / eye_width)
            )
            openness.append(np.linalg.norm(xy[top] - xy[bottom]) / eye_width)
        eye_center = (xy[33] + xy[263]) / 2
        eye_span = max(np.linalg.norm(xy[33] - xy[263]), 1)
        nose = (xy[1] - eye_center) / eye_span
        gaze = np.mean(values, axis=0)
        features = (float(gaze[0]), float(gaze[1]), float(nose[0]), float(nose[1]))
        return EyeObservation(features, min(openness) > 0.14, True)

    def detect(self, image):
        original = cv2.flip(image, 1) if self.backend is not None and self.input_mirrored else image
        rgb = cv2.cvtColor(original, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        result = self.model.process(rgb)
        if not result.multi_face_landmarks:
            return EyeObservation()
        points = result.multi_face_landmarks[0].landmark
        observation = self.extract(points, image.shape[1], image.shape[0])
        if self.backend is not None and observation.eyes_open:
            predicted = self.backend.predict(original, points)
            if not np.isfinite(predicted).all():
                return EyeObservation(face_present=True)
            # Comparable feature units keep calibration stability checks consistent.
            divisor = 10 if self.backend.kind == "itracker" else 1
            predicted = 0.5 * np.tanh(predicted / divisor)
            observation.features = tuple(float(value) for value in predicted) + tuple(
                observation.features[2:]
            )
        for index in (468, 473):
            x = (
                1 - points[index].x
                if self.backend is not None and self.input_mirrored
                else points[index].x
            )
            point = (int(x * image.shape[1]), int(points[index].y * image.shape[0]))
            cv2.circle(image, point, 4, (162, 232, 181), -1, cv2.LINE_AA)
            cv2.circle(image, point, 9, (162, 232, 181), 1, cv2.LINE_AA)
        return observation

    def close(self):
        try:
            self.model.close()
        finally:
            if self.backend is not None:
                self.backend.close()


class GazeController:
    """Smooth aiming, closure gating, and opt-in dwell with move-to-rearm behavior."""

    def __init__(self):
        self._position = None
        self._time = None
        self._anchor = None
        self._dwell_start = None
        self._clicked = False
        self._visible_since = None
        self._calibration_data = None
        self._calibration = None
        self.progress = 0
        self._last_click_position = None

    def reset(self, clear_click=False):
        self._position = self._time = self._anchor = self._dwell_start = None
        self._visible_since = None
        self._clicked = False
        self.progress = 0
        if clear_click:
            self._last_click_position = None

    def update(self, observation, settings, screen, now=None):
        now = time.monotonic() if now is None else now
        if self._time is not None and now - self._time > 0.25:
            self.reset()
        data = settings.get("eye_calibration")
        if data != self._calibration_data:
            self.reset(clear_click=True)
            self._calibration_data = data
            try:
                self._calibration = GazeCalibration(data)
            except ValueError:
                self._calibration = None
        if not observation.eyes_open or observation.features is None or self._calibration is None:
            self.reset()
            return []
        if (
            self._calibration.screen != tuple(screen)
            or data.get("camera_index", settings.get("camera_index"))
            != settings.get("camera_index")
            or data.get("mirror", settings.get("mirror_camera")) != settings.get("mirror_camera")
            or data.get("model", "mediapipe") != settings.get("eye_model", "mediapipe")
        ):
            self.reset()
            return []
        target = self._calibration.predict(observation.features)
        if target is None:
            self.reset()
            return []
        if self._visible_since is None:
            self._visible_since = now
        # Require stable visibility after a blink or lost face before resuming input.
        if now - self._visible_since < 0.2:
            return []
        if self._position is None:
            self._position = target
        elapsed = min(0.2, max(0.001, now - (self._time if self._time is not None else now - 0.03)))
        self._time = now
        distance = math.dist(target, self._position)
        # Fast for large gaze shifts; stronger smoothing for small fixation jitter.
        tau = 0.06 if distance > 0.1 else 0.18
        alpha = 1 - math.exp(-elapsed / tau)
        self._position = tuple(
            old + alpha * (new - old) for old, new in zip(self._position, target)
        )
        events = [Gesture("move_absolute", self._position)]
        if not settings.get("dwell_click_enabled"):
            self._anchor = self._dwell_start = None
            self._clicked = False
            self.progress = 0
            return events
        # Use unsmoothed gaze so a moving gaze cannot appear artificially stable.
        if self._last_click_position is not None:
            if math.dist(target, self._last_click_position) <= 0.07:
                self.progress = 0
                return events
            self._last_click_position = None
        if self._anchor is None or math.dist(target, self._anchor) > 0.035:
            self._anchor, self._dwell_start, self._clicked = target, now, False
        self.progress = min(1, (now - self._dwell_start) / settings["dwell_seconds"])
        if self.progress >= 1 and not self._clicked:
            events.extend([Gesture("left_click_down"), Gesture("left_click_up")])
            self._clicked = True
            self._last_click_position = target
        return events


def create_eye_tracker(settings):
    from src.eye.model_registry import model_directory

    name = settings.get("eye_model", "mediapipe")
    backend = None
    if name == "itracker":
        from src.eye.appearance_models import ITrackerModel

        backend = ITrackerModel(model_directory(settings))
    elif name in ("l2cs", "gazetr"):
        from src.eye.appearance_models import TorchGazeModel

        backend = TorchGazeModel(name, model_directory(settings))
    try:
        return EyeTracker(backend)
    except Exception:
        if backend is not None:
            backend.close()
        raise
