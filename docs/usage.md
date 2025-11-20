# How to Use HandGhost

This document explains how to use the HandGhost application.

## Running the Application

After installing dependencies, run the application from the project's root directory:
```bash
python main.py
```
This will launch the main HandGhost graphical user interface (GUI).

## The Main Interface

The application window is divided into two main parts:
1.  **Camera Feed (Left):** This area shows the view from your webcam and renders the "ghost hand" overlay.
2.  **Settings Panel (Right):** This panel contains all the controls and customizations for the application.

To begin, click the **"Start Tracking"** button. To stop, click **"Stop Tracking"**.

## Settings & Customization

All settings can be adjusted in the panel on the right. To make your changes permanent, click the **"Save Settings"** button at the bottom. This will save your configuration to a `settings.json` file for the next time you launch the app.

### General Settings
-   **Camera:** Choose from a list of available webcams.
-   **Pinch Threshold:** Adjusts how close your fingers need to be to register a "pinch".
-   **Mouse Sensitivity:** Controls how fast the cursor moves in relation to your hand movement.
-   **Enable Media Controls:** A checkbox to turn media control gestures on or off (disabled by default).

### Gesture Mapping
This section allows you to fully customize the control scheme. For each **Action** (like "Left Click"), you can assign a **Primitive Gesture** from the dropdown menu.

## Default Gestures

The default configuration is a two-handed scheme:

### Right Hand (Movement & Media)
-   **Activate Cursor Movement:** The default is `right_hand_index_pinch` (pinch your index finger and thumb together).
-   **Move Cursor:** While holding the activation pinch, move your hand.
-   **Media Controls (when enabled):**
    -   **Mute:** `right_hand_fist`
    -   **Next Track:** `right_hand_swipe_right` (not yet implemented)
    -   **Previous Track:** `right_hand_swipe_left` (not yet implemented)
    -   **Volume Up:** `right_hand_swipe_up` (not yet implemented)
    -   **Volume Down:** `right_hand_swipe_down` (not yet implemented)

### Left Hand (Clicks)
-   **Left Click:** `left_hand_index_pinch` (pinch your index finger and thumb together).
-   **Right Click:** `left_hand_middle_pinch` (pinch your middle finger and thumb together).

## Troubleshooting

-   **Cursor is choppy or not moving:**
    -   Ensure you are using the gesture assigned to the "Activate Movement" action.
    -   Try moving to an area with better lighting and a plain background.
    -   Adjust the "Mouse Sensitivity" in the settings panel.

-   **Clicks are not registering:**
    -   Adjust the "Pinch Threshold" in the settings panel.
    -   Ensure your fingers are clearly visible to the camera.

-   **Application shows an error or does not start:**
    -   Ensure you have installed all dependencies from `requirements.txt`.
    -   Verify that your webcam is connected and working correctly with other applications.
    -   If you have just built the executable, make sure you are running it from the `dist` folder.
