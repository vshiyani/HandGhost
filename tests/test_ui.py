"""GUI smoke checks run under Xvfb or a real graphical session."""

import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

from src.tracking.worker import TrackingFrame
from src.utils.settings_manager import SettingsManager


class PreviewWorker:
    def __init__(self, settings):
        self.settings = settings
        self.running = False
        self.error = ""
        self.packet = None

    def start(self):
        self.running = True
        self.packet = TrackingFrame(np.full((480, 640, 3), (30, 45, 35), dtype=np.uint8), 30, 12, 0)

    def pause(self):
        self.settings.set_setting("controls_enabled", False)

    def stop(self):
        self.pause()
        self.running = False

    def take_latest(self):
        packet, self.packet = self.packet, None
        return packet


@unittest.skipUnless(os.environ.get("DISPLAY") or os.name == "nt", "requires graphical display")
class TestUI(unittest.TestCase):
    def setUp(self):
        from src.ui.app_ui import HandGhostGUI

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.settings = SettingsManager(Path(self.tmp.name) / "settings.json")
        self.app = HandGhostGUI(self.settings, PreviewWorker)
        self.addCleanup(self.close)
        self.app.update()

    def close(self):
        if self.app.winfo_exists():
            self.app.on_closing()
            self.app.update()

    def test_navigation_preview_opt_in_pause_and_save(self):
        app = self.app
        self.assertIn("HandGhost", app.title())
        self.assertFalse(self.settings.get_setting("controls_enabled"))
        app.toggle_tracking()
        app._tick()
        app.update()
        self.assertEqual(app.metrics["fps"].cget("text"), "30 fps")
        self.assertFalse(app.empty_state.winfo_ismapped())
        app.controls_var.set(True)
        app._toggle_controls()
        self.assertTrue(self.settings.get_setting("controls_enabled"))
        app.pause_controls()
        self.assertFalse(self.settings.get_setting("controls_enabled"))
        app.show_page("Preferences")
        app.update()
        self.assertTrue(app.preferences.winfo_ismapped())
        app.save_and_apply_settings()
        self.assertTrue(self.settings.settings_file.exists())
        app.show_page("Gesture guide")
        app.update()
        self.assertTrue(app.guide.winfo_ismapped())
        app.show_page("Studio")
        app.toggle_tracking()
        app._tick()
        app.update()
        self.assertTrue(app.empty_state.winfo_ismapped())

    def test_invalid_camera_and_duplicate_gesture_feedback(self):
        from src.ui.app_ui import POSE_LABELS

        self.app.camera_var.set("invalid")
        self.app.toggle_tracking()
        self.assertFalse(self.app.worker.running)
        self.assertIn("camera index", self.app.notice.cget("text"))
        mapping = self.settings.get_setting("gestures")
        self.app._remap("right_click", POSE_LABELS[mapping["left_click"]])
        self.assertEqual(self.settings.get_setting("gestures"), mapping)
        self.assertIn("already assigned", self.app.notice.cget("text"))

    def test_eye_mode_requires_calibration_before_input(self):
        from tests.test_eye_tracking import calibration

        app = self.app
        app._change_mode("Eyes")
        app.update()
        self.assertEqual(self.settings.get_setting("tracking_mode"), "eyes")
        self.assertTrue(app.eye_panel.winfo_ismapped())
        app.toggle_tracking()
        app._tick()
        app.controls_var.set(True)
        app._toggle_controls()
        self.assertFalse(self.settings.get_setting("controls_enabled"))
        data = calibration()
        data["screen"] = list(app.worker.screen)
        app._save_calibration(data)
        app.controls_var.set(True)
        app._toggle_controls()
        self.assertTrue(self.settings.get_setting("controls_enabled"))
        app._set_preference("mirror_camera", False)
        self.assertFalse(self.settings.get_setting("controls_enabled"))
        self.assertFalse(app._has_calibration())

    def test_switching_gaze_models_restores_separate_calibrations(self):
        from src.eye.model_registry import MODELS
        from tests.test_eye_tracking import calibration

        app = self.app
        app._change_mode("Eyes")
        data = calibration()
        data["screen"] = list(app.worker.screen)
        app._save_calibration(data)
        self.assertTrue(app._has_calibration())
        app._change_model(MODELS["l2cs"].label)
        self.assertIsNone(self.settings.get_setting("eye_calibration"))
        app.toggle_tracking()
        self.assertFalse(app.worker.running)
        self.assertIn("needs setup", app.notice.cget("text"))
        app._change_model(MODELS["mediapipe"].label)
        self.assertTrue(app._has_calibration())
