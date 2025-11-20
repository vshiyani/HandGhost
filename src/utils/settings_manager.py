import json
import os
from src.utils.logger import Logger

class SettingsManager:
    def __init__(self, settings_file="settings.json"):
        self.logger = Logger.get_logger(__name__)
        self.settings_file = settings_file
        self.settings = self._load_default_settings()
        self.load_settings()

    def _load_default_settings(self):
        return {
            "camera_index": 0,
            "pinch_threshold": 30.0,
            "mouse_sensitivity": 2.5,
            "smoothing_factor": 0.7,
            "media_control_enabled": False,
            "gestures": {
                "activate_movement": "right_hand_index_pinch",
                "left_click": "left_hand_index_pinch",
                "right_click": "left_hand_middle_pinch",
                "volume_up": "right_hand_swipe_up",
                "volume_down": "right_hand_swipe_down",
                "next_track": "right_hand_swipe_right",
                "prev_track": "right_hand_swipe_left",
                "mute": "right_hand_fist"
            }
        }

    def load_settings(self):
        """Loads settings from the JSON file."""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    loaded_settings = json.load(f)
                    # Merge loaded settings with defaults to ensure all keys are present
                    self.settings.update(loaded_settings)
                    self.logger.info("Settings loaded successfully.")
            except (json.JSONDecodeError, TypeError) as e:
                self.logger.error(f"Error loading settings file: {e}. Using default settings.")
        else:
            self.logger.info("No settings file found. Using default settings and creating a new file.")
            self.save_settings()

    def save_settings(self):
        """Saves the current settings to the JSON file."""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=4)
            self.logger.info("Settings saved successfully.")
        except IOError as e:
            self.logger.error(f"Error saving settings file: {e}")

    def get_setting(self, key):
        """Gets a specific setting value."""
        return self.settings.get(key)

    def set_setting(self, key, value):
        """Sets a specific setting value."""
        self.settings[key] = value
