import copy
import unittest

import numpy as np

from src.eye.gaze_tracker import EyeObservation, EyeTracker, GazeCalibration, GazeController
from src.utils.settings_manager import DEFAULTS

TARGETS = [(x, y) for y in (0.12, 0.5, 0.88) for x in (0.12, 0.5, 0.88)]
FEATURES = [
    [(x - 0.5) * 0.3, (y - 0.5) * 0.2, (x - 0.5) * 0.04, (y - 0.5) * 0.04] for x, y in TARGETS
]


def calibration():
    return GazeCalibration.fit(FEATURES, TARGETS, (1600, 1000))


class TestEyeCalibration(unittest.TestCase):
    def test_fit_predict_and_reload_coefficients(self):
        model = GazeCalibration(calibration())
        np.testing.assert_allclose(model.predict(FEATURES[4]), (0.5, 0.5), atol=0.02)
        self.assertLess(model.error, 0.1)
        self.assertIsNone(model.predict([10, 10, 0, 0]))
        self.assertIsNone(model.predict([float("nan"), 0, 0, 0]))

    def test_rejects_unobservable_or_inconsistent_calibration(self):
        with self.assertRaisesRegex(ValueError, "Too little"):
            GazeCalibration.fit(np.zeros((9, 4)), TARGETS, (1600, 1000))
        rng = np.random.default_rng(42)
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            GazeCalibration.fit(rng.random((9, 4)), TARGETS, (1600, 1000))

    def test_rejects_corrupt_saved_model(self):
        for value in (None, {}, {"version": 1, "mean": []}):
            with self.assertRaises(ValueError):
                GazeCalibration(value)
        data = calibration()
        data["weights"][0][0] = float("inf")
        with self.assertRaises(ValueError):
            GazeCalibration(data)

    def test_eye_feature_extraction_detects_open_and_closed_eyes(self):
        from types import SimpleNamespace

        points = [SimpleNamespace(x=0.0, y=0.0) for _ in range(478)]
        for index, x, y in (
            (33, 0.3, 0.4),
            (133, 0.4, 0.4),
            (362, 0.6, 0.4),
            (263, 0.7, 0.4),
            (468, 0.35, 0.4),
            (473, 0.65, 0.4),
            (159, 0.35, 0.38),
            (145, 0.35, 0.42),
            (386, 0.65, 0.38),
            (374, 0.65, 0.42),
            (1, 0.5, 0.55),
        ):
            points[index] = SimpleNamespace(x=x, y=y)
        observation = EyeTracker.extract(points, 640, 480)
        self.assertTrue(observation.eyes_open)
        self.assertTrue(observation.face_present)
        np.testing.assert_allclose(observation.features[:2], (0, 0), atol=0.001)
        points[145].y = points[159].y
        self.assertFalse(EyeTracker.extract(points, 640, 480).eyes_open)

    def test_real_face_model_accepts_blank_image(self):
        tracker = EyeTracker()
        self.addCleanup(tracker.close)
        observation = tracker.detect(np.zeros((480, 640, 3), dtype=np.uint8))
        self.assertFalse(observation.face_present)
        self.assertIsNone(observation.features)


class TestGazeController(unittest.TestCase):
    def setUp(self):
        self.controller = GazeController()
        self.settings = copy.deepcopy(DEFAULTS)
        self.settings["eye_calibration"] = calibration()
        self.observation = EyeObservation(FEATURES[4], True, True)
        self.screen = (1600, 1000)

    def update(self, now, observation=None):
        return self.controller.update(
            observation or self.observation, self.settings, self.screen, now
        )

    def test_calibration_and_open_eyes_required_before_aiming(self):
        self.assertEqual(self.update(0), [])
        events = self.update(0.3)
        self.assertEqual([e.type for e in events], ["move_absolute"])
        self.assertEqual(self.update(0.4, EyeObservation(FEATURES[4], False, True)), [])
        self.assertEqual(self.update(0.5), [])
        self.assertEqual(len(self.update(0.8)), 1)
        self.settings["eye_calibration"] = None
        self.assertEqual(self.update(1), [])

    def test_screen_or_camera_change_prevents_aiming(self):
        self.screen = (1920, 1080)
        self.assertEqual(self.update(0), [])
        self.assertEqual(self.update(1), [])
        self.screen = (1600, 1000)
        self.settings["eye_calibration"]["camera_index"] = 5
        self.assertEqual(self.update(2), [])

    def feed(self, seconds, observation=None):
        events = []
        clock = getattr(self, "clock", 0)
        for _ in range(round(seconds / 0.05)):
            clock += 0.05
            events.extend(self.update(clock, observation))
        self.clock = clock
        return [event.type for event in events]

    def test_dwell_is_opt_in_and_only_clicks_once_until_look_away(self):
        self.assertNotIn("left_click_down", self.feed(2))
        self.settings["dwell_click_enabled"] = True
        self.assertEqual(self.feed(1.5).count("left_click_down"), 1)
        self.assertNotIn("left_click_down", self.feed(2))
        # Normal blinking must not rearm another click at the same location.
        self.feed(0.2, EyeObservation(FEATURES[4], False, True))
        self.assertNotIn("left_click_down", self.feed(2))
        self.observation = EyeObservation(FEATURES[5], True, True)
        self.assertEqual(self.feed(1.5).count("left_click_down"), 1)

    def test_gaze_movement_resets_dwell(self):
        self.settings["dwell_click_enabled"] = True
        self.feed(0.9)
        self.observation = EyeObservation(FEATURES[5], True, True)
        self.assertNotIn("left_click_down", self.feed(0.3))
        self.assertLess(self.controller.progress, 0.3)
        self.assertEqual(self.feed(1.3).count("left_click_down"), 1)

    def test_stalled_frames_cannot_complete_a_dwell(self):
        self.settings["dwell_click_enabled"] = True
        self.update(0)
        self.update(0.3)
        self.assertEqual(self.update(2), [])
        self.assertEqual(self.controller.progress, 0)
