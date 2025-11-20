import unittest
import numpy as np
from src.detection.hand_detector import HandDetector

class TestHandDetector(unittest.TestCase):
    """
    Tests for the HandDetector class.
    """
    def setUp(self):
        self.detector = HandDetector()

    def test_detect_no_hands(self):
        """
        Tests that no hands are detected in a blank image.
        """
        # Create a blank image
        image = np.zeros((100, 100, 3), dtype=np.uint8)

        hands = self.detector.detect(image)
        self.assertIsNone(hands)

if __name__ == '__main__':
    unittest.main()
