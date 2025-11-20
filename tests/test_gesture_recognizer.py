import unittest
from src.gesture.gesture_recognizer import GestureRecognizer

class TestGestureRecognizer(unittest.TestCase):
    """
    Tests for the GestureRecognizer class.
    """
    def setUp(self):
        self.recognizer = GestureRecognizer()

    def test_recognize_no_hands(self):
        """
        Tests that no gestures are recognized when there are no hands.
        """
        gestures = self.recognizer.recognize(None)
        self.assertEqual(len(gestures), 0)

if __name__ == '__main__':
    unittest.main()
