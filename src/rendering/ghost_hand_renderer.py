import cv2
import mediapipe as mp
from src.utils.logger import Logger
from src.gesture.gesture_recognizer import Gesture # Import Gesture class

class GhostHandRenderer:
    """
    Renders the ghost hand overlay.
    """
    # MediaPipe hand landmark indices - duplicated here for convenience in rendering logic
    # In a larger project, these might be in a shared config or enum
    THUMB_TIP = 4
    INDEX_FINGER_TIP = 8

    def __init__(self, opacity=0.5, landmark_color=(0, 255, 0), connection_color=(255, 255, 255), thickness=2):
        self.logger = Logger.get_logger(__name__)
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_hands = mp.solutions.hands
        self.opacity = opacity
        self.thickness = thickness

        self.base_landmark_drawing_spec = self.mp_drawing.DrawingSpec(
            color=landmark_color, thickness=self.thickness, circle_radius=self.thickness
        )
        self.base_connection_drawing_spec = self.mp_drawing.DrawingSpec(
            color=connection_color, thickness=self.thickness
        )

        # Specific drawing spec for active gestures
        self.active_gesture_landmark_color = (0, 0, 255) # Red for active gesture
        self.active_gesture_connection_color = (0, 0, 255)

    def draw(self, image, hands, gestures=[]):
        """
        Draws the ghost hand overlay on the given image.

        Args:
            image: The image to draw on.
            hands: A list of detected hands, with their landmarks.
            gestures: A list of recognized Gesture objects for visual feedback.

        Returns:
            The image with the ghost hand overlay.
        """
        overlay = image.copy()
        output = image.copy()

        if hands:
            for hand_landmarks in hands:
                landmark_drawing_spec = self.base_landmark_drawing_spec
                connection_drawing_spec = self.base_connection_drawing_spec

                # Check for active click gesture to change color
                is_clicking = any(g.type == "left_click" for g in gestures)
                if is_clicking:
                    landmark_drawing_spec = self.mp_drawing.DrawingSpec(
                        color=self.active_gesture_landmark_color, thickness=self.thickness, circle_radius=self.thickness
                    )
                    connection_drawing_spec = self.mp_drawing.DrawingSpec(
                        color=self.active_gesture_connection_color, thickness=self.thickness
                    )

                self.mp_drawing.draw_landmarks(
                    overlay,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    landmark_drawing_spec=landmark_drawing_spec,
                    connection_drawing_spec=connection_drawing_spec
                )
        
        # Blend the overlay with the original image
        output = cv2.addWeighted(overlay, self.opacity, output, 1 - self.opacity, 0)
        return output
