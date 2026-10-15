import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS

import numpy as np

from src.gesture.gesture_recognizer import GestureRecognizer
from src.utils.settings_manager import SettingsManager


def make_hand(label="Left", pose="index", x=0.5, scale=1):
    # Open hand with a palm width of 0.2. Synthetic landmarks isolate pose logic.
    coords = [(0.5, 0.9)] * 21
    coords[5], coords[17] = (0.4, 0.65), (0.6, 0.65)
    for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18)):
        coords[tip], coords[pip] = (0.5, 0.2), (0.5, 0.5)
    coords[4] = (0.25, 0.3)
    if pose == "index":
        coords[8] = (0.26, 0.3)
    elif pose == "middle":
        coords[12] = (0.26, 0.3)
    elif pose == "fist":
        for tip in (8, 12, 16, 20):
            coords[tip] = (0.5, 0.85)
    points = [NS(x=(px - 0.5) * scale + x, y=py * scale, z=0) for px, py in coords]
    return NS(landmark=points), NS(classification=[NS(label=label)])


class TestGestureRecognizer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.settings = SettingsManager(Path(self.tmp.name) / "settings.json")
        self.recognizer = GestureRecognizer(self.settings)
        self.frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def recognize(self, hand=None, now=1):
        if hand is None:
            return self.recognizer.recognize([], [], self.frame, now=now)
        return self.recognizer.recognize([hand[0]], [hand[1]], self.frame, now=now)

    def types(self, events):
        return [event.type for event in events]

    def test_no_hands(self):
        self.assertEqual(self.recognize(), [])

    def test_pinch_debounces_holds_and_releases_on_hand_loss(self):
        hand = make_hand()
        self.assertEqual(self.recognize(hand), [])
        self.assertEqual(self.types(self.recognize(hand)), ["left_click_down"])
        self.assertEqual(self.recognize(hand), [])
        self.assertEqual(self.types(self.recognize()), ["left_click_up"])
        self.assertEqual(self.recognize(), [])

    def test_hysteresis_prevents_click_chatter(self):
        hand = make_hand()
        self.recognize(hand)
        self.recognize(hand)
        hand[0].landmark[8].x = 0.32  # .07/.2=.35: above press .3, below release .405
        self.assertEqual(self.recognize(hand), [])
        hand[0].landmark[8].x = 0.35
        self.assertEqual(self.types(self.recognize(hand)), ["left_click_up"])

    def test_pinch_is_relative_to_palm_size(self):
        for scale in (0.5, 1, 1.8):
            self.recognizer.reset()
            hand = make_hand(scale=scale)
            self.recognize(hand)
            self.assertEqual(self.types(self.recognize(hand)), ["left_click_down"])

    def test_relative_movement_does_not_jump_on_activation(self):
        hand = make_hand("Right")
        self.recognize(hand)
        self.assertEqual(self.recognize(hand), [])
        moved = make_hand("Right", x=0.55)
        events = self.recognize(moved)
        self.assertEqual(self.types(events), ["move_relative"])
        self.assertAlmostEqual(events[0].data[0], 32)
        self.recognize()
        self.recognize(moved)
        self.assertEqual(self.recognize(moved), [])

    def test_scroll_has_deadzone_and_direction(self):
        hand = make_hand("Right", "middle")
        self.recognize(hand)
        self.recognize(hand)
        hand[0].landmark[8].y -= 0.01
        self.assertEqual(self.recognize(hand), [])
        hand[0].landmark[8].y -= 0.04
        events = self.recognize(hand)
        self.assertEqual(self.types(events), ["scroll"])
        self.assertGreater(events[0].data, 0)

    def test_media_is_opt_in_and_fires_once_per_pose(self):
        hand = make_hand("Right", "fist")
        self.recognize(hand)
        self.assertEqual(self.recognize(hand), [])
        self.recognize()
        self.settings.set_setting("media_control_enabled", True)
        self.recognize(hand)
        self.assertEqual(self.types(self.recognize(hand)), ["mute"])
        self.assertEqual(self.recognize(hand, now=3), [])

    def test_remapping_releases_previous_drag(self):
        hand = make_hand()
        self.recognize(hand)
        self.recognize(hand)
        mapping = self.settings.get_setting("gestures")
        mapping["left_click"] = "None"
        self.settings.set_setting("gestures", mapping)
        self.assertEqual(self.types(self.recognize(hand)), ["left_click_up"])
