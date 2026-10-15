import unittest

import numpy as np

from src.detection.hand_detector import HandDetector


class TestHandDetector(unittest.TestCase):
    def test_blank_frame_loads_bundled_model_and_detects_no_hands(self):
        detector = HandDetector()
        self.addCleanup(detector.close)
        self.assertEqual(detector.detect(np.zeros((480, 640, 3), dtype=np.uint8)), ([], []))
