import pyautogui
from src.utils.logger import Logger
from src.utils.settings_manager import SettingsManager

# Disable the fail-safe to allow cursor to move to screen corners
pyautogui.FAILSAFE = False

class OSInteraction:
    """
    Interacts with the operating system (e.g., mouse, keyboard).
    """
    def __init__(self, settings_manager: SettingsManager):
        self.logger = Logger.get_logger(__name__)
        self.settings_manager = settings_manager
        self.screen_width, self.screen_height = pyautogui.size()
        
        # Load settings
        self.sensitivity = self.settings_manager.get_setting("mouse_sensitivity")
        self.smoothing_factor = self.settings_manager.get_setting("smoothing_factor")
        self.camera_width = 1280 # Default, will be updated from GUI
        self.camera_height = 720 # Default

        # State for smoothing
        self.smoothed_x = 0
        self.smoothed_y = 0
        self.logger.info(f"Screen resolution detected: {self.screen_width}x{self.screen_height}")

    def set_sensitivity(self, sensitivity):
        """
        Sets the mouse sensitivity.
        """
        self.sensitivity = sensitivity
        self.settings_manager.set_setting("mouse_sensitivity", sensitivity)
        self.logger.info(f"Mouse sensitivity set to: {self.sensitivity}")

    def perform_action(self, gesture):
        """
        Performs an action based on the given gesture.

        Args:
            gesture: The gesture to perform an action for.
        """
        # Map generic click actions to specific pyautogui calls
        action_map = {
            "left_click_down": lambda: pyautogui.mouseDown(button='left', _pause=False),
            "left_click_up": lambda: pyautogui.mouseUp(button='left', _pause=False),
            "right_click_down": lambda: pyautogui.mouseDown(button='right', _pause=False),
            "right_click_up": lambda: pyautogui.mouseUp(button='right', _pause=False),
            "mute": lambda: pyautogui.press('volumemute', _pause=False),
            "next_track": lambda: pyautogui.press('nexttrack', _pause=False),
            "prev_track": lambda: pyautogui.press('prevtrack', _pause=False),
            "volume_up": lambda: pyautogui.press('volumeup', _pause=False),
            "volume_down": lambda: pyautogui.press('volumedown', _pause=False),
        }

        if gesture.type == "move_relative":
            delta_x, delta_y = gesture.data
            move_x = delta_x * self.sensitivity
            move_y = delta_y * self.sensitivity
            self.smoothed_x = (move_x * (1 - self.smoothing_factor)) + (self.smoothed_x * self.smoothing_factor)
            self.smoothed_y = (move_y * (1 - self.smoothing_factor)) + (self.smoothed_y * self.smoothing_factor)
            pyautogui.move(self.smoothed_x, self.smoothed_y, _pause=False)
        
        elif gesture.type in action_map:
            if "down" in gesture.type: # Reset smoothing on any new click
                self.smoothed_x = 0
                self.smoothed_y = 0
            action_map[gesture.type]()
            self.logger.info(f"Performed action: {gesture.type}")