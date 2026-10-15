import itertools
import threading
import unittest
from unittest.mock import Mock

import numpy as np

from src.tracking.worker import TrackingFrame, TrackingWorker
from src.utils.settings_manager import SettingsManager


class TestTrackingWorker(unittest.TestCase):
    def setUp(self):
        self.settings = SettingsManager("/nonexistent/handghost-worker.json")

    def test_latest_frame_mailbox_discards_old_frames(self):
        worker = TrackingWorker(self.settings)
        worker._publish(TrackingFrame(hands=1))
        worker._publish(TrackingFrame(hands=2))
        self.assertEqual(worker.take_latest().hands, 2)
        self.assertIsNone(worker.take_latest())

    def test_inference_failure_releases_camera_model_and_mouse(self):
        camera, detector, interaction = Mock(), Mock(), Mock()
        camera.get_camera.return_value.read.return_value = (
            True,
            np.zeros((100, 100, 3), dtype=np.uint8),
        )
        detector.detect.side_effect = RuntimeError("model failed")
        worker = TrackingWorker(
            self.settings, lambda index: camera, lambda: detector, lambda settings: interaction
        )
        with self.assertLogs("src.tracking.worker", level="ERROR"):
            worker.start()
            worker.thread.join(3)
        self.assertFalse(worker.running)
        self.assertEqual(worker.error, "model failed")
        camera.release_camera.assert_called_once()
        detector.close.assert_called_once()
        interaction.release_all.assert_called_once()
        self.assertFalse(self.settings.get_setting("controls_enabled"))

    def test_stop_discards_input_and_releases_owned_resources(self):
        camera, detector, interaction = Mock(), Mock(), Mock()
        camera.get_camera.return_value.read.return_value = (
            True,
            np.zeros((100, 100, 3), dtype=np.uint8),
        )
        detected = threading.Event()

        def detect(image):
            detected.set()
            return [], []

        detector.detect.side_effect = detect
        worker = TrackingWorker(
            self.settings, lambda index: camera, lambda: detector, lambda settings: interaction
        )
        worker.start()
        self.assertTrue(detected.wait(3))
        worker.stop()
        worker.thread.join(3)
        self.assertFalse(worker.running)
        self.assertEqual(worker.error, "")
        camera.release_camera.assert_called_once()
        detector.close.assert_called_once()
        interaction.release_all.assert_called()
        interaction.perform_action.assert_not_called()

    def test_camera_open_failure_is_actionable(self):
        camera = Mock()
        camera.get_camera.return_value = None
        worker = TrackingWorker(self.settings, lambda index: camera)
        with self.assertLogs("src.tracking.worker", level="ERROR"):
            worker.start()
            worker.thread.join(3)
        self.assertIn("Camera unavailable", worker.error)
        camera.release_camera.assert_called_once()

    def test_eye_mode_uses_only_eye_model_and_dispatches_aim(self):
        from src.eye.gaze_tracker import EyeObservation, GazeController
        from tests.test_eye_tracking import FEATURES, calibration

        self.settings.set_setting("tracking_mode", "eyes")
        self.settings.set_setting("eye_calibration", calibration())
        self.settings.set_setting("controls_enabled", True)
        camera, detector, interaction = Mock(), Mock(), Mock()
        camera.get_camera.return_value.read.return_value = (
            True,
            np.zeros((100, 100, 3), dtype=np.uint8),
        )
        detector.detect.return_value = EyeObservation(FEATURES[4], True, True)
        dispatched = threading.Event()
        interaction.perform_action.side_effect = lambda event: dispatched.set()
        hand_factory = Mock()
        timestamps = itertools.count(0, 0.05)
        worker = TrackingWorker(
            self.settings,
            lambda index: camera,
            hand_factory,
            lambda settings: interaction,
            eye_detector_factory=lambda: detector,
            gaze_controller_factory=lambda: GazeController(clock=lambda: next(timestamps)),
        )
        worker.screen = (1600, 1000)
        from unittest.mock import patch

        with patch("src.tracking.worker.desktop_capability") as capability:
            capability.return_value.available = True
            worker.start()
            try:
                self.assertTrue(
                    dispatched.wait(3),
                    f"{worker.error}; eye frames={detector.detect.call_count}; "
                    f"controls={self.settings.get_setting('controls_enabled')}",
                )
            finally:
                worker.stop()
                worker.thread.join(3)
        hand_factory.assert_not_called()
        self.assertEqual(interaction.perform_action.call_args.args[0].type, "move_absolute")
        detector.close.assert_called_once()
        camera.release_camera.assert_called_once()

    def test_stop_releases_input_even_while_camera_read_is_blocked(self):
        entered, unblock = threading.Event(), threading.Event()
        camera, detector, interaction = Mock(), Mock(), Mock()

        def read():
            entered.set()
            unblock.wait(3)
            return False, None

        camera.get_camera.return_value.read.side_effect = read
        worker = TrackingWorker(
            self.settings, lambda index: camera, lambda: detector, lambda settings: interaction
        )
        worker.start()
        try:
            self.assertTrue(entered.wait(3))
            worker.stop()
            interaction.release_all.assert_called()
            self.assertTrue(worker.running)
        finally:
            unblock.set()
            worker.thread.join(3)
        self.assertFalse(worker.running)
