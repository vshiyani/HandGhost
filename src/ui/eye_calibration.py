"""Nine-point gaze calibration. Escape always cancels; capture never stores images."""

import time
import tkinter as tk

import customtkinter as ctk
import numpy as np

from src.eye.gaze_tracker import GazeCalibration


class EyeCalibrationWindow(ctk.CTkToplevel):
    TARGETS = [
        (0.5, 0.5),
        (0.12, 0.12),
        (0.5, 0.12),
        (0.88, 0.12),
        (0.12, 0.5),
        (0.88, 0.5),
        (0.12, 0.88),
        (0.5, 0.88),
        (0.88, 0.88),
    ]

    def __init__(self, parent, read_features, completed):
        super().__init__(parent)
        self._read = read_features
        self._completed = completed
        self._index = 0
        self._samples = []
        self._features = []
        self._last_timestamp = 0
        self._capturing = False
        self._timer = None
        self._screen = (self.winfo_screenwidth(), self.winfo_screenheight())
        self.configure(fg_color="#101413")
        self.geometry(f"{self._screen[0]}x{self._screen[1]}+0+0")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.canvas = tk.Canvas(self, bg="#101413", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.title("HandGhost · Eye calibration")
        self.bind("<space>", self.capture)
        self.bind("<Escape>", lambda event: self.cancel())
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.after(150, self._show_target)
        self.after(200, self.focus_force)
        self.grab_set()

    def _show_target(self):
        self.canvas.delete("all")
        width, height = self._screen
        self.canvas.create_text(
            width / 2,
            34,
            text=f"EYE CALIBRATION  ·  {self._index + 1} / 9",
            fill="#B5E8A2",
            font=("Arial", 14, "bold"),
        )
        self.instructions = self.canvas.create_text(
            width / 2,
            64,
            text="Keep your head still. Look at the dot, then press Space.   Esc to cancel.",
            fill="#EDF3EE",
            font=("Arial", 15),
        )
        x, y = self.TARGETS[self._index]
        x, y = x * width, y * height
        self.canvas.create_oval(x - 24, y - 24, x + 24, y + 24, outline="#496243", width=2)
        self.dot = self.canvas.create_oval(x - 9, y - 9, x + 9, y + 9, fill="#B5E8A2", outline="")
        self.canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill="#101413", outline="")

    def capture(self, event=None):
        if self._capturing:
            return
        self._capturing = True
        self._samples = []
        self._started = time.monotonic()
        self.canvas.itemconfigure(self.instructions, text="Hold your gaze on the dot…")
        self._collect()

    def _collect(self):
        features, timestamp = self._read()
        now = time.monotonic()
        if features is not None and timestamp > self._last_timestamp and now - timestamp < 0.25:
            self._samples.append(features)
            self._last_timestamp = timestamp
        if now - self._started < 1.0:
            self._timer = self.after(30, self._collect)
            return
        self._capturing = False
        samples = np.asarray(self._samples)
        if len(samples) < 10:
            self.canvas.itemconfigure(
                self.instructions,
                text="Eyes not visible long enough. Check lighting, look at the dot, and press Space again.",
            )
            return
        if np.max(samples[:, :2].std(axis=0)) > 0.045:
            self.canvas.itemconfigure(
                self.instructions,
                text="Gaze was moving. Keep looking at the dot and press Space to retry.",
            )
            return
        self._features.append(np.median(samples, axis=0).tolist())
        self._index += 1
        if self._index < len(self.TARGETS):
            self._show_target()
            return
        try:
            calibration = GazeCalibration.fit(self._features, self.TARGETS, self._screen)
        except ValueError as exc:
            self.canvas.delete("all")
            width, height = self._screen
            self.canvas.create_text(
                width / 2,
                height / 2,
                text=str(exc) + "\n\nPress Esc and choose Calibrate gaze to try again.",
                fill="#E5BB79",
                font=("Arial", 18),
                width=width - 160,
                justify="center",
            )
            # Space must not try to collect a tenth target after a failed fit.
            self.unbind("<space>")
            return
        self._completed(calibration)
        self.cancel()

    def cancel(self):
        if self._timer is not None:
            self.after_cancel(self._timer)
        self.grab_release()
        self.destroy()
