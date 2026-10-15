import unittest
from unittest.mock import Mock, patch

from src.gesture.gesture_recognizer import Gesture
from src.interaction.os_interaction import OSInteraction, desktop_capability
from src.utils.settings_manager import SettingsManager


class TestOSInteraction(unittest.TestCase):
    def setUp(self):
        self.backend = Mock()
        self.backend.FAILSAFE = True
        self.settings = SettingsManager("/nonexistent/handghost-test.json")
        self.interaction = OSInteraction(self.settings, self.backend)

    def test_buttons_release_on_pause_even_at_failsafe_corner(self):
        self.interaction.perform_action(Gesture("left_click_down"))
        self.interaction.release_all()
        self.backend.mouseUp.assert_called_once_with(button="left", _pause=False)
        self.assertTrue(self.backend.FAILSAFE)
        self.interaction.release_all()
        self.assertEqual(self.backend.mouseUp.call_count, 1)

    def test_automation_failure_releases_drag_and_propagates(self):
        self.interaction.perform_action(Gesture("left_click_down"))
        self.backend.move.side_effect = RuntimeError("fail-safe")
        with self.assertRaisesRegex(RuntimeError, "fail-safe"):
            self.interaction.perform_action(Gesture("move_relative", (5, 5)))
        self.backend.mouseUp.assert_called_once()
        self.assertTrue(self.backend.FAILSAFE)

    def test_media_and_scroll_dispatch(self):
        self.interaction.perform_action(Gesture("mute"))
        self.backend.press.assert_called_with("volumemute", _pause=False)
        self.interaction.perform_action(Gesture("scroll", -2))
        self.backend.scroll.assert_called_with(-2, _pause=False)

    @patch("src.interaction.os_interaction.sys.platform", "linux")
    def test_wayland_is_preview_only_even_with_xwayland_display(self):
        with patch.dict("os.environ", {"XDG_SESSION_TYPE": "wayland", "DISPLAY": ":0"}, clear=True):
            self.assertFalse(desktop_capability().available)
        with patch.dict("os.environ", {"XDG_SESSION_TYPE": "x11", "DISPLAY": ":0"}, clear=True):
            self.assertTrue(desktop_capability().available)
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(desktop_capability().available)

    def test_absolute_gaze_maps_to_desktop_coordinates(self):
        self.backend.size.return_value = (1600, 1000)
        self.interaction.perform_action(Gesture("move_absolute", (0.5, 0.5)))
        self.backend.moveTo.assert_called_once_with(799, 499, _pause=False)


class TestVirtualDesktop(unittest.TestCase):
    def test_real_x11_pointer_and_button_release(self):
        import os
        import sys

        if (
            os.environ.get("HANDGHOST_TEST_DESKTOP") != "1"
            or not sys.platform.startswith("linux")
            or not os.environ.get("DISPLAY")
            or os.environ.get("WAYLAND_DISPLAY")
        ):
            self.skipTest("requires X11 desktop")
        from unittest.mock import patch

        import pyautogui
        from Xlib import X, display

        settings = SettingsManager("/nonexistent/handghost-x11.json")
        interaction = OSInteraction(settings)
        connection = display.Display()
        try:
            # Move away from fail-safe corners for the isolated test desktop.
            with patch.object(pyautogui, "FAILSAFE", False):
                pyautogui.moveTo(300, 300)
            interaction.perform_action(Gesture("move_relative", (20, 10)))
            self.assertGreater(pyautogui.position().x, 300)
            interaction.perform_action(Gesture("left_click_down"))
            self.assertTrue(connection.screen().root.query_pointer().mask & X.Button1Mask)
            interaction.release_all()
            self.assertFalse(connection.screen().root.query_pointer().mask & X.Button1Mask)
            interaction.perform_action(Gesture("move_absolute", (0.5, 0.5)))
            width, height = pyautogui.size()
            self.assertEqual(
                tuple(pyautogui.position()), (int((width - 1) / 2), int((height - 1) / 2))
            )
        finally:
            interaction.release_all()
            connection.close()
