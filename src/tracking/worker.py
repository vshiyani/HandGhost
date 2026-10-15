"""One paced worker and one latest-frame slot: latency cannot build up in a queue."""

import logging
import threading
import time
from dataclasses import dataclass

import cv2

from src.camera.camera_manager import CameraManager
from src.detection.hand_detector import HandDetector
from src.eye.gaze_tracker import GazeController, create_eye_tracker
from src.gesture.gesture_recognizer import GestureRecognizer
from src.interaction.os_interaction import OSInteraction, desktop_capability
from src.rendering.ghost_hand_renderer import GhostHandRenderer


@dataclass
class TrackingFrame:
    image: object = None
    fps: float = 0
    latency_ms: float = 0
    hands: int = 0
    gesture: str = "Ready for your hands"
    error: str = ""
    eye_features: object = None
    eyes_open: bool = False
    dwell_progress: float = 0


class TrackingWorker:
    def __init__(
        self,
        settings_manager,
        camera_factory=CameraManager,
        detector_factory=HandDetector,
        interaction_factory=OSInteraction,
        eye_detector_factory=None,
        gaze_controller_factory=GazeController,
    ):
        self.settings = settings_manager
        self._camera_factory = camera_factory
        self._detector_factory = detector_factory
        self._interaction_factory = interaction_factory
        self._eye_detector_factory = eye_detector_factory
        self._gaze_controller_factory = gaze_controller_factory
        self.screen = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._input_lock = threading.RLock()
        self._interaction = None
        self._latest = None
        self.thread = None
        self.error = ""

    @property
    def running(self):
        return self.thread is not None and self.thread.is_alive()

    def start(self):
        if self.running:
            return
        self._stop.clear()
        self.error = ""
        self.thread = threading.Thread(target=self._run, name="handghost-tracking", daemon=True)
        self.thread.start()

    def pause(self):
        self.settings.set_setting("controls_enabled", False)
        try:
            self._release_input()
        except Exception:
            logging.getLogger(__name__).exception("Unable to release desktop input")

    def stop(self):
        self._stop.set()
        self.pause()

    def _release_input(self):
        with self._input_lock:
            if self._interaction is not None:
                self._interaction.release_all()

    def take_latest(self):
        with self._lock:
            frame, self._latest = self._latest, None
        return frame

    def _publish(self, frame):
        with self._lock:
            self._latest = frame

    def _run(self):
        camera = detector = interaction = None
        try:
            settings = self.settings.snapshot()
            camera = self._camera_factory(settings["camera_index"])
            capture = camera.get_camera(
                settings["camera_width"], settings["camera_height"], settings["target_fps"]
            )
            if capture is None:
                raise RuntimeError(
                    "Camera unavailable. Check its index, permissions, and whether another app is using it."
                )
            eye_mode = settings["tracking_mode"] == "eyes"
            detector = (
                (
                    self._eye_detector_factory()
                    if self._eye_detector_factory
                    else create_eye_tracker(settings)
                )
                if eye_mode
                else self._detector_factory()
            )
            gaze = self._gaze_controller_factory()
            recognizer = GestureRecognizer(self.settings)
            renderer = GhostHandRenderer()
            interaction = self._interaction_factory(self.settings)
            with self._input_lock:
                self._interaction = interaction
            last = time.monotonic()
            fps = 0
            missed = 0
            was_enabled = False
            input_error = ""
            while not self._stop.is_set():
                started = time.monotonic()
                ok, image = capture.read()
                if not ok:
                    self._release_input()
                    recognizer.reset()
                    gaze.reset()
                    self.settings.set_setting("controls_enabled", False)
                    missed += 1
                    if missed >= 5:
                        raise RuntimeError(
                            "Camera stopped sending frames. Reconnect it and start again."
                        )
                    self._stop.wait(0.05)
                    continue
                missed = 0
                settings = self.settings.snapshot()
                if settings["mirror_camera"]:
                    image = cv2.flip(image, 1)
                observation = None
                hands, handedness = [], []
                if eye_mode:
                    detector.input_mirrored = settings["mirror_camera"]
                    observation = detector.detect(image)
                else:
                    hands, handedness = detector.detect(image)
                    # MediaPipe assumes mirrored input for handedness classification.
                    if not settings["mirror_camera"]:
                        for item in handedness:
                            item.classification[0].label = (
                                "Left" if item.classification[0].label == "Right" else "Right"
                            )
                settings = self.settings.snapshot()
                enabled = settings["controls_enabled"] and desktop_capability().available
                if enabled != was_enabled:
                    self._release_input()
                    recognizer.reset()
                    gaze.reset(clear_click=True)
                if eye_mode:
                    events = gaze.update(observation, settings, self.screen or (0, 0))
                else:
                    events = recognizer.recognize(hands, handedness, image)
                if enabled and not self._stop.is_set():
                    try:
                        for event in events:
                            if self._stop.is_set() or not self.settings.get_setting(
                                "controls_enabled"
                            ):
                                self._release_input()
                                break
                            with self._input_lock:
                                if not self._stop.is_set() and self.settings.get_setting(
                                    "controls_enabled"
                                ):
                                    interaction.perform_action(event)
                    except Exception as exc:
                        self.settings.set_setting("controls_enabled", False)
                        enabled = False
                        input_error = "Input paused. " + str(exc)
                        self._release_input()
                        recognizer.reset()
                if enabled:
                    input_error = ""
                if (not eye_mode and not hands) or (eye_mode and not observation.eyes_open):
                    self._release_input()
                was_enabled = enabled
                display = image if eye_mode else renderer.draw(image, hands, events)
                # RGB conversion happens off the Tk thread, once per produced frame.
                rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
                elapsed = time.monotonic() - started
                interval = time.monotonic() - last
                last = time.monotonic()
                instant = 1 / max(interval, 0.001)
                fps = instant if not fps else fps * 0.85 + instant * 0.15
                actions = [event.type.replace("_", " ") for event in events]
                message = ", ".join(actions) or (
                    "Hands detected" if hands else "Ready for your hands"
                )
                if eye_mode:
                    if not observation.face_present:
                        message = "Bring your face into view"
                    elif not observation.eyes_open:
                        message = "Eyes closed · input paused"
                    elif settings["eye_calibration"] is None:
                        message = "Eyes detected · calibrate to aim"
                    else:
                        message = (
                            "Gaze aiming"
                            if events
                            else "Hold your head steady · recalibrate if needed"
                        )
                self._publish(
                    TrackingFrame(
                        image=rgb,
                        fps=fps,
                        latency_ms=elapsed * 1000,
                        hands=int(observation.face_present) if eye_mode else len(hands),
                        gesture=message,
                        error=input_error,
                        eye_features=observation.features if eye_mode else None,
                        eyes_open=observation.eyes_open if eye_mode else False,
                        dwell_progress=gaze.progress if eye_mode else 0,
                    )
                )
                self._stop.wait(max(0, 1 / settings["target_fps"] - elapsed))
        except Exception as exc:
            self.error = str(exc)
            logging.getLogger(__name__).exception("Tracking stopped")
            self._publish(TrackingFrame(error=self.error))
        finally:
            self.settings.set_setting("controls_enabled", False)
            for resource, method in (
                (interaction, "release_all"),
                (detector, "close"),
                (camera, "release_camera"),
            ):
                if resource is not None:
                    try:
                        with self._input_lock:
                            getattr(resource, method)()
                    except Exception:
                        logging.getLogger(__name__).exception("Unable to release %s", method)
