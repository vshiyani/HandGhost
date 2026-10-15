import json
import tempfile
import unittest
from pathlib import Path

from src.utils.settings_manager import SettingsManager


class TestSettings(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "nested/settings.json"

    def test_launch_never_creates_files_or_arms_controls(self):
        settings = SettingsManager(self.path)
        self.assertFalse(self.path.exists())
        settings.set_setting("controls_enabled", True)
        settings.save_settings()
        self.assertFalse(json.loads(self.path.read_text())["controls_enabled"])
        self.assertFalse(SettingsManager(self.path).get_setting("controls_enabled"))

    def test_invalid_json_and_types_fall_back_safely(self):
        self.path.parent.mkdir()
        self.path.write_text('{"target_fps": "fast", "mouse_sensitivity": null, "gestures": []}')
        settings = SettingsManager(self.path)
        self.assertEqual(settings.get_setting("target_fps"), 30)
        settings.set_setting("smoothing_factor", 100)
        self.assertEqual(settings.get_setting("smoothing_factor"), 0.9)
        settings.set_setting("target_fps", float("nan"))
        self.assertEqual(settings.get_setting("target_fps"), 30)
        self.path.write_text("{broken")
        self.assertEqual(SettingsManager(self.path).get_setting("camera_index"), 0)

    def test_nested_snapshots_cannot_mutate_live_preferences(self):
        settings = SettingsManager(self.path)
        snapshot = settings.snapshot()
        snapshot["gestures"]["left_click"] = "None"
        self.assertNotEqual(settings.get_setting("gestures")["left_click"], "None")

    def test_legacy_swipes_are_replaced_and_duplicates_disarmed(self):
        settings = SettingsManager(self.path)
        settings.set_setting(
            "gestures", {"mute": "right_hand_swipe_right", "right_click": "left_hand_index_pinch"}
        )
        self.assertEqual(settings.get_setting("gestures")["mute"], "right_hand_fist")
        self.assertEqual(settings.get_setting("gestures")["right_click"], "None")
