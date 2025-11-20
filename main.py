from src.ui.app_ui import HandGhostGUI
from src.utils.settings_manager import SettingsManager

def main():
    """
    Main entry point for the HandGhost application.
    Initializes the SettingsManager and the GUI.
    """
    settings_manager = SettingsManager()
    app = HandGhostGUI(settings_manager)
    app.run()

if __name__ == "__main__":
    main()
