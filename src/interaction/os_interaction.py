"""Lazy desktop automation, with an explicit Linux session capability check."""

import os
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class DesktopCapability:
    available: bool
    label: str
    detail: str


def desktop_capability():
    if sys.platform.startswith("linux"):
        if os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" or os.environ.get(
            "WAYLAND_DISPLAY"
        ):
            return DesktopCapability(
                False,
                "Wayland · preview only",
                "Tracking works here. Full desktop control needs an X11 session; sign in using Xorg.",
            )
        if not os.environ.get("DISPLAY"):
            return DesktopCapability(
                False,
                "No desktop display",
                "Open HandGhost in a graphical X11 session, or use Xvfb for automated checks.",
            )
        return DesktopCapability(
            True,
            "Linux · X11",
            "Desktop controls are available. Move to a screen corner to stop input.",
        )
    if sys.platform == "darwin":
        return DesktopCapability(
            True, "macOS", "Allow Camera and Accessibility access in System Settings."
        )
    return DesktopCapability(True, "Windows", "Allow camera access in Windows privacy settings.")


class OSInteraction:
    def __init__(self, settings_manager, backend=None):
        self.settings_manager = settings_manager
        self.backend = backend
        self._held = set()
        self._smooth = (0.0, 0.0)
        self._screen = None

    def _get_backend(self):
        if self.backend is None:
            capability = desktop_capability()
            if not capability.available:
                raise RuntimeError(capability.detail)
            import pyautogui

            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0
            self.backend = pyautogui
        return self.backend

    def perform_action(self, gesture):
        backend = self._get_backend()
        try:
            if gesture.type == "move_relative":
                settings = self.settings_manager.snapshot()
                factor = settings["smoothing_factor"]
                gain = settings["mouse_sensitivity"]
                self._smooth = tuple(
                    old * factor + delta * gain * (1 - factor)
                    for old, delta in zip(self._smooth, gesture.data)
                )
                backend.move(*self._smooth, _pause=False)
            elif gesture.type == "move_absolute":
                if self._screen is None:
                    self._screen = backend.size()
                x, y = gesture.data
                backend.moveTo(
                    int(x * (self._screen[0] - 1)), int(y * (self._screen[1] - 1)), _pause=False
                )
            elif gesture.type in ("left_click_down", "right_click_down"):
                button = gesture.type.split("_")[0]
                backend.mouseDown(button=button, _pause=False)
                self._held.add(button)
            elif gesture.type in ("left_click_up", "right_click_up"):
                button = gesture.type.split("_")[0]
                backend.mouseUp(button=button, _pause=False)
                self._held.discard(button)
            elif gesture.type == "scroll":
                backend.scroll(gesture.data, _pause=False)
            elif gesture.type in ("mute", "volume_up", "volume_down", "next_track", "prev_track"):
                key = {
                    "mute": "volumemute",
                    "volume_up": "volumeup",
                    "volume_down": "volumedown",
                    "next_track": "nexttrack",
                    "prev_track": "prevtrack",
                }[gesture.type]
                backend.press(key, _pause=False)
        except Exception:
            self.release_all()
            raise

    def release_all(self):
        self._smooth = (0.0, 0.0)
        if self.backend is None:
            return
        # A fail-safe at a screen corner must not prevent releasing a held drag.
        failsafe = self.backend.FAILSAFE
        try:
            self.backend.FAILSAFE = False
            for button in tuple(self._held):
                self.backend.mouseUp(button=button, _pause=False)
                self._held.discard(button)
        finally:
            self.backend.FAILSAFE = failsafe
