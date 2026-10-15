"""Lightweight hand overlay drawn directly into the worker's display frame."""

import cv2
import mediapipe as mp


class GhostHandRenderer:
    def __init__(self):
        self.connections = mp.solutions.hands.HAND_CONNECTIONS

    def draw(self, image, hands, gestures=()):
        if not hands:
            return image
        height, width = image.shape[:2]
        active = any(gesture.type.endswith("_down") for gesture in gestures)
        color = (121, 229, 174) if not active else (100, 200, 255)
        for hand in hands:
            points = [(int(point.x * width), int(point.y * height)) for point in hand.landmark]
            for start, end in self.connections:
                cv2.line(image, points[start], points[end], color, 2, cv2.LINE_AA)
            for index, point in enumerate(points):
                cv2.circle(
                    image, point, 5 if index in (4, 8, 12, 16, 20) else 3, color, -1, cv2.LINE_AA
                )
        return image
