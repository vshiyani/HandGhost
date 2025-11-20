from src.utils.logger import Logger
from src.utils.settings_manager import SettingsManager
import mediapipe as mp
import time

class Gesture:
    """
    Represents a recognized application-level action.
    """
    def __init__(self, type, data=None):
        self.type = type
        self.data = data

class GestureRecognizer:
    """
    Detects a set of primitive gestures and maps them to application actions
    based on user-configurable settings.
    """
    PRIMITIVE_GESTURES = [
        "None", "left_hand_index_pinch", "left_hand_middle_pinch", "left_hand_fist",
        "right_hand_index_pinch", "right_hand_middle_pinch", "right_hand_fist"
    ]

    # MediaPipe hand landmark indices
    THUMB_TIP = 4
    INDEX_FINGER_TIP = 8
    MIDDLE_FINGER_TIP = 12
    RING_FINGER_TIP = 16
    PINKY_TIP = 20
    INDEX_FINGER_PIP = 6
    MIDDLE_FINGER_PIP = 10
    RING_FINGER_PIP = 14
    PINKY_FINGER_PIP = 18

    def __init__(self, settings_manager: SettingsManager):
        self.logger = Logger.get_logger(__name__)
        self.settings_manager = settings_manager
        
        self.primitive_states = {gesture: False for gesture in self.PRIMITIVE_GESTURES}
        self.prev_move_x = None
        self.prev_move_y = None

    def recognize(self, all_hands_landmarks, all_hands_handedness, image):
        detected_gestures = []
        image_height, image_width, _ = image.shape
        
        pinch_thresh = self.settings_manager.get_setting("pinch_threshold") / 1000.0
        gesture_mapping = self.settings_manager.get_setting("gestures")
        
        newly_detected_primitives = {gesture: False for gesture in self.PRIMITIVE_GESTURES}
        
        active_move_hand_landmarks = None
        activate_primitive = gesture_mapping.get("activate_movement")
        move_hand_label_needed = "left" if "left" in activate_primitive else "right"

        for hand_landmarks, handedness_obj in zip(all_hands_landmarks, all_hands_handedness):
            hand_label = handedness_obj.classification[0].label.lower()

            thumb_tip = hand_landmarks.landmark[self.THUMB_TIP]
            index_tip = hand_landmarks.landmark[self.INDEX_FINGER_TIP]
            middle_tip = hand_landmarks.landmark[self.MIDDLE_FINGER_TIP]

            if self._get_distance(index_tip, thumb_tip) < pinch_thresh:
                newly_detected_primitives[f"{hand_label}_hand_index_pinch"] = True
            if self._get_distance(middle_tip, thumb_tip) < pinch_thresh:
                newly_detected_primitives[f"{hand_label}_hand_middle_pinch"] = True
            if self._is_fist(hand_landmarks):
                newly_detected_primitives[f"{hand_label}_hand_fist"] = True

            if hand_label == move_hand_label_needed:
                active_move_hand_landmarks = hand_landmarks

        # --- Handle Discrete Actions (Clicks) ---
        for primitive, is_active in newly_detected_primitives.items():
            was_active = self.primitive_states[primitive]
            if is_active and not was_active:
                action = self._find_action_for_primitive(gesture_mapping, primitive)
                if action and action != "activate_movement":
                    detected_gestures.append(Gesture(type=f"{action}_down"))
            elif not is_active and was_active:
                action = self._find_action_for_primitive(gesture_mapping, primitive)
                if action and action != "activate_movement":
                    detected_gestures.append(Gesture(type=f"{action}_up"))
            self.primitive_states[primitive] = is_active

        # --- Handle Continuous Action (Movement) ---
        if newly_detected_primitives.get(activate_primitive) and active_move_hand_landmarks:
            move_x, move_y = self._get_landmark_coordinates(active_move_hand_landmarks, self.INDEX_FINGER_TIP, image_width, image_height)
            
            if self.prev_move_x is not None:
                delta_x = move_x - self.prev_move_x
                delta_y = move_y - self.prev_move_y
                detected_gestures.append(Gesture(type="move_relative", data=(delta_x, delta_y)))
            
            self.prev_move_x = move_x
            self.prev_move_y = move_y
        else:
            self.prev_move_x = None
            self.prev_move_y = None
            
        return detected_gestures

    def _find_action_for_primitive(self, gesture_mapping, primitive):
        for action, prim in gesture_mapping.items():
            if prim == primitive:
                return action
        return None

    def _get_distance(self, p1, p2):
        return ((p1.x - p2.x)**2 + (p1.y - p2.y)**2)**0.5

    def _get_landmark_coordinates(self, hand_landmarks, landmark_index, image_width, image_height):
        landmark = hand_landmarks.landmark[landmark_index]
        x = int(landmark.x * image_width)
        y = int(landmark.y * image_height)
        return x, y

    def _is_fist(self, hand_landmarks):
        return (self._is_finger_closed(hand_landmarks, self.INDEX_FINGER_TIP, self.INDEX_FINGER_PIP) and
                self._is_finger_closed(hand_landmarks, self.MIDDLE_FINGER_TIP, self.MIDDLE_FINGER_PIP) and
                self._is_finger_closed(hand_landmarks, self.RING_FINGER_TIP, self.RING_FINGER_PIP) and
                self._is_finger_closed(hand_landmarks, self.PINKY_TIP, self.PINKY_FINGER_PIP))

    def _is_finger_closed(self, hand_landmarks, finger_tip_index, pip_index):
        tip = hand_landmarks.landmark[finger_tip_index]
        pip = hand_landmarks.landmark[pip_index]
        wrist = hand_landmarks.landmark[0]
        return self._get_distance(tip, wrist) < self._get_distance(pip, wrist)
