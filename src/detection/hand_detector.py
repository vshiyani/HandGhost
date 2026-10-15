"""Reusable CPU hand model. Models ship in the pinned MediaPipe wheel."""

import cv2
import mediapipe as mp


class HandDetector:
    def __init__(self, max_num_hands=2, min_detection_confidence=0.6, min_tracking_confidence=0.6):
        self.hands = mp.solutions.hands.Hands(
            max_num_hands=max_num_hands,
            model_complexity=0,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def detect(self, image):
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.hands.process(rgb)
        return results.multi_hand_landmarks or [], results.multi_handedness or []

    def close(self):
        self.hands.close()
