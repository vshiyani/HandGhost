Project: HandGhost – Agentic AI-Designed Hand-Tracking Desktop Controller
1. Purpose & Scope

This document specifies requirements for:

An Agentic AI System (“the Agent”) that:

Designs and implements a desktop application.

Iteratively tests and refines the application using feedback and telemetry.

The Target Application (“HandGhost App”) that:

Uses the computer’s webcam to detect and track a user’s hand and finger joints in real time.

Renders a semi-transparent “ghost hand” overlay on the screen.

Allows the user to control the mouse cursor and interact with windows using hand gestures (click, drag, move/resize windows).

Provides additional gesture-based features (shortcuts, media control, etc.).

The initial version may target one OS (e.g. Windows or macOS) with a design that is extensible to others.

2. Stakeholders & Users

End User: Person who wants a hands-free, gesture-based way to control their computer.

Agent Orchestrator / Developer: The entity that runs and supervises the Agent (e.g., user interacting with an LLM dev agent).

Agent (LLM + Tools): Autonomous coding assistant that:

Reads this document.

Plans implementation.

Writes, runs, and debugs code.

Produces installable artifacts.

3. High-Level Goals

Enable accurate, low-latency hand tracking via webcam.

Provide a visual ghost-hand overlay aligned with the user’s real hand.

Allow basic desktop interaction:

Move cursor.

Single/double click.

Click-and-drag for window moving and resizing.

Basic scrolling.

Provide cool, optional features:

Gesture-controlled media (play/pause, volume).

App shortcuts via hand poses.

Multi-monitor support.

Ensure privacy, safety, and usability:

Explicit camera permission.

Local processing (no video sent to cloud by default).

Easy calibration and exit gestures.

4. System Overview
4.1 Agentic AI System

The Agent should:

Ingest this requirements document.

Ask the user any missing critical questions (OS, hardware constraints) once at the start.

Generate:

A technical design/architecture.

Implementation plan (milestones).

Source code for the HandGhost App.

Build scripts and packaging.

Basic documentation and a quick-start guide.

Use tools (as provided by its environment) to:

Search documentation (e.g. OS APIs, libraries).

Create and edit files.

Run tests.

Execute the compiled application.

Iterate until acceptance criteria (Section 11) are met.

4.2 HandGhost Application Main Components

Camera & Input Module

Enumerates webcams.

Captures video frames at configurable FPS and resolution.

Hand Detection & Joint Tracking Module

Runs a hand pose model (e.g., based on CNN/Landmark models) to obtain:

Hand(s) bounding boxes.

Finger joint coordinates (x,y).

Hand orientation (palm vs back, left vs right if possible).

Gesture Recognition Engine

Translates raw joint data into:

Cursor position.

Click events.

Drag actions.

Scroll gestures.

Special poses (shortcuts, media control).

Ghost Hand Rendering Layer

Draws semi-transparent hand skeleton/mesh overlay on top of the operating system desktop (or in a dedicated full-screen overlay window).

OS Interaction Layer

Moves system cursor.

Generates mouse events (click, drag, scroll).

Optionally manipulates windows (move, resize, snap).

Configuration & UI Module

GUI for:

Camera selection, sensitivity, calibration.

Gesture mapping and toggles.

Onboarding wizard.

Logging & Telemetry Module

Local logs for debugging.

Optional, anonymized metrics (if user opts in).

5. Functional Requirements – Agent

A-FR-1 The Agent shall read and internalize this requirements document as its primary spec.

A-FR-2 The Agent shall clarify:

Target OS (e.g., “Windows 11 on x86_64”).

Preferred language/stack (if any).

GPU availability (if relevant).

A-FR-3 The Agent shall generate a technical design document covering:

Architecture diagram / description.

Selected libraries (e.g., OpenCV, MediaPipe, OS automation libraries).

Data flow from webcam to pointer events.

Performance targets and constraints.

A-FR-4 The Agent shall implement the HandGhost App codebase, including:

Application entrypoint.

Core modules listed in Section 4.2.

Build/packaging for the target OS (e.g., MSI/EXE for Windows, .app/.dmg for macOS).

A-FR-5 The Agent shall create and run automated tests where feasible:

Unit tests for gesture logic.

Integration tests for model loading.

If full UI automation is not feasible, provide test harnesses and manual test steps.

A-FR-6 The Agent shall provide documentation:

README / quickstart.

“How to calibrate and use gestures”.

Troubleshooting section.

A-FR-7 The Agent shall iterate:

Run the app.

Inspect logs/errors.

Apply fixes.

Repeat until basic use cases work (see Section 11).

6. Functional Requirements – HandGhost Core
6.1 Webcam Access & Setup

FR-1 The app shall detect available webcams and let the user choose one.

FR-2 The app shall request explicit permission to access the camera and show a clear status indicator when camera is active.

FR-3 The app shall support at least:

720p at 30 FPS (if hardware allows).

Automatic fallback to lower resolutions if performance is insufficient.

6.2 Hand & Joint Tracking

FR-4 The app shall detect at least one hand reliably within the camera’s field of view.

FR-5 The app should support two hands when hardware/model performance allows; primary control may default to dominant hand.

FR-6 The app shall estimate positions of key joints per detected hand:

Wrist.

All finger joints (MCP, PIP, DIP, fingertip).

FR-7 The tracking latency (capture → result) should target < 100 ms on typical hardware; must not exceed 200 ms under normal conditions.

FR-8 The app shall handle partial occlusions (e.g., fingers overlapping) gracefully and avoid erratic jumps when tracking confidence is low.

6.3 Ghost Hand Rendering

FR-9 The app shall render a semi-transparent ghost hand overlay representing:

Finger bone segments.

Joints as small circles or nodes.

FR-10 The ghost overlay shall be visually distinct yet non-intrusive (configurable opacity and thickness).

FR-11 The ghost hand shall track the user’s real hand in real time, with minimal visible lag.

FR-12 There shall be a visual indicator when a gesture is recognized (e.g., highlight color when “click” is active).

6.4 Cursor & OS Interaction

FR-13 The app shall map hand position to on-screen cursor position:

Provide at least one mapping mode:

Absolute: Hand position maps directly to screen coordinates.

Relative: Hand movement translates to cursor movement from its current location.

User shall be able to switch between modes.

FR-14 The app shall support basic mouse actions via gestures:

Single click.

Double click.

Right click.

Click-and-drag (for moving windows or dragging items).

Scroll (e.g., vertical scroll via two-finger swipe).

FR-15 Gestures shall be configurably mapped, e.g.:

Pinch thumb + index to trigger click.

Maintain pinch and move hand to drag.

Swipe up/down gesture to scroll.

FR-16 The app shall expose configuration UI to:

Adjust gesture sensitivity (distance thresholds, smoothing).

Enable/disable specific gestures.

Swap left/right click mapping for left-handed users.

6.5 Window Management Features

FR-17 The app shall support moving windows via gestures, e.g.:

Gesture to “grab window title bar” when ghost hand is over it.

Move hand to drag the window.

Release gesture to drop window.

FR-18 The app should support resize operations:

Gesture to grab window edge/corner when ghost hand is near it.

Move hand to resize.

FR-19 The app should support snap actions (e.g., snap left/right half, full-screen) via distinct gestures or quick hand motions.

7. “Cool” Optional Features

These are nice-to-have features the Agent should consider implementing if time/resources allow. They should be modular and togglable.

7.1 Shortcut & Macro Gestures

FR-20 User shall be able to assign specific hand poses or gestures to:

Launch applications (e.g., browser, terminal).

Send keyboard shortcuts (e.g., Ctrl+S, Cmd+Tab).

Trigger macros (sequence of keystrokes/mouse events).

Example:

“Victory sign” = Alt+Tab.

“Open palm with fingers spread” = Show desktop.

7.2 Media & Volume Control

FR-21 Support basic media controls via gestures:

Play/pause.

Next/previous track.

Volume up/down.

Mute.

Example:

Swipe right = next track.

Rotate hand clockwise = volume up.

7.3 Multi-Monitor Support

FR-22 If multiple monitors are connected, the app shall:

Provide a configuration for monitor layout.

Allow gestures to move cursor between monitors (e.g., flick towards screen edge, or specific gesture to cycle screens).

7.4 Mode Switching & Privacy

FR-23 Provide a global “gesture off/on” toggle:

Keyboard shortcut (e.g., Ctrl+Alt+G).

Optional “X” hand gesture to quickly disable control without touching the keyboard.

FR-24 Provide a “Privacy Mode”:

Temporarily stop reading frames from camera (or discard results).

Show clear indication when privacy mode is active.

7.5 Recording & Replay

FR-25 (Advanced) Allow user to record a gesture sequence and rebind it:

Record the motion + mapped actions.

Assign to a named shortcut.

Invoke later via a “trigger pose”.

8. Calibration & Onboarding

FR-26 On first launch, the app shall guide user through a calibration wizard:

Position hand within a bounding box in camera view.

Set dominant hand.

Adjust sensitivity (coarse/fine movements).

Verify click and drag gestures.

FR-27 Calibration data shall be saved and loaded on subsequent runs.

FR-28 User shall be able to rerun calibration anytime from the settings UI.

9. Non-Functional Requirements
9.1 Performance

NFR-1 Target end-to-end latency (from camera capture to cursor update) of < 100 ms, with a hard upper bound of 200 ms under normal system load.

NFR-2 CPU usage should ideally remain under 30–40% on a mid-range system; GPU can be used if available.

NFR-3 Memory usage should be within reasonable bounds for a desktop app (e.g., under 1GB in typical operation).

9.2 Reliability & Stability

NFR-4 The app shall handle:

Loss of camera (disconnected) gracefully.

Temporary model failures by restarting the model or notifying the user.

NFR-5 The app shall not crash the OS or interfere with essential system services.

9.3 Usability

NFR-6 The app shall provide:

Clear UI text and tooltips for gestures and settings.

Visual feedback when gestures are detected.

An easy way to exit the app (close window, tray icon menu, keyboard shortcut).

NFR-7 Defaults should be usable without requiring advanced configuration.

9.4 Portability

NFR-8 The design should make OS-specific components pluggable:

Separate interface for OS interaction (mouse/windows).

Separate interface for camera access.

Allows future ports to other OSes (e.g., Linux, VR environments).

10. Security & Privacy Requirements

SEC-1 All video processing should be local by default:

No frames uploaded to remote servers unless explicitly enabled by the user.

SEC-2 The app shall clearly indicate when the camera is in use (e.g., tray icon, overlay, or light).

SEC-3 If cloud services (e.g., model hosting, update checks) are used, inform the user in settings and obtain consent.

SEC-4 Logs should not contain raw images; only high-level information (e.g., gesture names, errors, timestamps).

SEC-5 Provide an option to delete all local telemetry and configuration data.

11. Acceptance Criteria

The Agent’s work is considered acceptable when:

Installation

A user can install the HandGhost App on the target OS using a standard installer package.

The app launches successfully and shows a main UI.

Core Interaction

With webcam on and calibration completed:

User can move the mouse cursor using hand movements.

User can perform:

Single left-click via gesture.

Click-and-drag to move a window.

A scroll gesture to scroll within a window.

The ghost hand overlay visibly tracks the real hand.

Latency & Smoothness

Cursor movement feels responsive (no more than 200 ms lag).

Ghost hand does not jitter excessively under normal lighting and distance.

Basic Window Management

User can pick up a window by “grabbing” its title bar.

User can move the window to another location.

User can release it by ending the grab gesture.

Configuration & Safety

User can:

Toggle camera on/off.

Toggle gesture control on/off.

Change sensitivity and major gesture mappings.

The app shows a clear indicator when camera is active.

Documentation

README / user guide exists that explains:

Installation.

Setup and calibration.

Default gestures.

How to exit/disable the app.

Known limitations and troubleshooting steps are documented.

At Least One “Cool Feature”

At least one optional feature from Section 7 is implemented and usable (e.g., a media-control gesture or app launch shortcut).

12. Future Extensions (Non-Required)

The Agent may propose—but is not required to implement—the following:

Depth cameras / AR devices integration (e.g., Leap Motion, VR controllers).

3D hand mesh rendering.

Multi-user support (different profiles).

AI customization:

Automatically learn user’s preferred motion patterns over time.

Personalized gesture recognition via few-shot examples.