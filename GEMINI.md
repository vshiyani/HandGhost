# GEMINI.md: HandGhost Project

This document provides context for the HandGhost project, an AI-powered hand-tracking desktop controller.

## Project Overview

HandGhost is a standalone desktop application that uses a computer's webcam to provide robust, gesture-based control over the mouse and media. It features a modern GUI that allows for extensive customization of gestures and sensitivity, with all settings saved between sessions.

The application was developed iteratively, starting from a basic skeleton and evolving based on user feedback into a feature-rich, user-friendly tool.

## Key Technologies

*   **Core Logic:** Python
*   **Hand Tracking:** MediaPipe
*   **Computer Vision:** OpenCV
*   **GUI:** CustomTkinter (for a modern look and feel)
*   **OS Interaction:** PyAutoGUI
*   **Packaging:** PyInstaller

## Project Structure

The codebase is organized into the following directories:

*   `src`: Contains the main source code, including:
    *   `ui/app_ui.py`: The main GUI application class.
    *   `utils/settings_manager.py`: Handles loading and saving of user settings.
    *   Modules for camera, detection, gesture recognition, rendering, and OS interaction.
*   `docs`: Contains project documentation (`README.md`, `usage.md`).
*   `HandGhost.spec`: The PyInstaller specification file for building the executable.
*   `settings.json`: The default settings file, created on first run.

## Running the Application

There are two ways to run HandGhost:

### 1. From Source Code

This is recommended for development.

**a. Setup Environment:**
Install all necessary dependencies from the `requirements.txt` file.
```bash
pip install -r requirements.txt
```

**b. Run the Application:**
Execute the `main.py` script.
```bash
python main.py
```

### 2. As a Standalone Executable

This is the recommended way for end-users.

**a. Build the Executable:**
Use PyInstaller with the provided `.spec` file. This command bundles the application and all its dependencies into a single `.exe` file in the `dist` directory.
```bash
python -m PyInstaller HandGhost.spec --clean
```

**b. Run the Executable:**
Navigate to the `dist` folder and run `HandGhost.exe`.

## Gesture Customization and Settings

HandGhost is highly customizable. A `settings.json` file is automatically created to store user preferences. The GUI provides an interface to:
-   Adjust mouse sensitivity and pinch detection thresholds.
-   Map different hand gestures (e.g., "left_hand_index_pinch") to various actions (e.g., "left_click", "activate_movement").
-   Enable/disable features like media controls.
-   Save settings to persist across application launches.
