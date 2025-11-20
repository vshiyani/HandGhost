import cv2
import mediapipe as mp
from src.utils.logger import Logger

class HandDetector:
    """
    Detects hands and landmarks in an image.
    """
    def __init__(self, max_num_hands=2, min_detection_confidence=0.5, min_tracking_confidence=0.5):
        self.logger = Logger.get_logger(__name__)
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

    def detect(self, image):
        """
        Detects hands in the given image.

        Args:
            image: The image to detect hands in.

        Returns:
            A tuple containing:
                - A list of detected hands, with their landmarks.
                - A list of handedness information for each detected hand.
        """
        # Convert the image to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image_rgb.flags.writeable = False # To improve performance

        # Process the image and find hands
        results = self.hands.process(image_rgb)

        image_rgb.flags.writeable = True # Re-enable writeable flag

        landmarks = results.multi_hand_landmarks if results.multi_hand_landmarks else []
        handedness = results.multi_handedness if results.multi_handedness else []
        
        if landmarks:
            self.logger.info(f"Hands detected: {len(landmarks)}")
        else:
            self.logger.info("No hands detected.")

        return landmarks, handedness
