"""HandGhost Studio. Tk owns the interface; the worker owns camera and inference."""

import threading
import time
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image

from src.camera.camera_manager import CameraManager
from src.eye.gaze_tracker import GazeCalibration
from src.eye.model_registry import MODELS, model_directory, model_status
from src.gesture.gesture_recognizer import GestureRecognizer
from src.interaction.os_interaction import desktop_capability
from src.tracking.worker import TrackingWorker
from src.ui.eye_calibration import EyeCalibrationWindow

ctk.set_appearance_mode("dark")
# Arial has scalable X11 aliases even on minimal Tk builds without Xft.
ctk.ThemeManager.theme["CTkFont"]["family"] = "Arial"

BG = "#101413"
SURFACE = "#181E1B"
RAISED = "#202823"
BORDER = "#303C34"
TEXT = "#EDF3EE"
MUTED = "#A0B0A5"
ACCENT = "#B5E8A2"
INK = "#192418"
AMBER = "#E5BB79"

ACTION_LABELS = {
    "activate_movement": "Move pointer",
    "left_click": "Click & drag",
    "right_click": "Right click",
    "scroll": "Scroll",
    "mute": "Mute audio",
    "volume_up": "Volume up",
    "volume_down": "Volume down",
    "next_track": "Next track",
    "prev_track": "Previous track",
}
POSE_LABELS = {"None": "Unassigned"}
POSE_LABELS.update(
    {
        primitive: primitive.replace("_hand_", " · ").replace("_", " ").title()
        for primitive in GestureRecognizer.PRIMITIVE_GESTURES
        if primitive != "None"
    }
)


class HandGhostGUI(ctk.CTk):
    def __init__(self, settings_manager, worker_factory=TrackingWorker):
        super().__init__()
        self.settings_manager = settings_manager
        self.worker = worker_factory(settings_manager)
        self.capability = desktop_capability()
        self._closing = False
        self._stop_requested = False
        self._last_frame = None
        self._last_photo = None
        self._last_size = None
        self._session_state = None
        self._last_metrics = 0
        self._notice_key = None
        self._eye_features = (None, 0)
        self._calibration_window = None
        self._model_installer = None
        self._model_install_result = None
        self.worker.screen = (self.winfo_screenwidth(), self.winfo_screenheight())
        self._message = ""
        self._message_until = 0
        self.title("HandGhost · Studio")
        self.geometry("1280x840")
        self.minsize(1080, 740)
        self.configure(fg_color=BG)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_rail()
        self.workspace = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.workspace.grid(row=0, column=1, sticky="nsew", padx=30, pady=26)
        self.workspace.grid_columnconfigure(0, weight=1)
        self.workspace.grid_rowconfigure(2, weight=1)
        self._build_header()
        self.studio = self._build_studio()
        self.preferences = self._build_preferences()
        self.guide = self._build_guide()
        self.pages = {
            "Studio": self.studio,
            "Preferences": self.preferences,
            "Gesture guide": self.guide,
        }
        self.show_page("Studio")
        self._refresh_mode()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.bind("<Escape>", self.pause_controls)
        self.after(33, self._tick)

    def label(self, parent, text, size=14, color=TEXT, weight="normal", **kwargs):
        return ctk.CTkLabel(
            parent,
            text=text,
            text_color=color,
            font=ctk.CTkFont(family="Arial", size=size, weight=weight),
            **kwargs,
        )

    def card(self, parent, **kwargs):
        return ctk.CTkFrame(
            parent,
            fg_color=SURFACE,
            border_color=BORDER,
            border_width=1,
            corner_radius=18,
            **kwargs,
        )

    def button(self, parent, text, command, primary=False, **kwargs):
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            fg_color=ACCENT if primary else RAISED,
            hover_color="#C6F1B5" if primary else BORDER,
            text_color=INK if primary else TEXT,
            corner_radius=10,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            **kwargs,
        )

    def _build_rail(self):
        rail = ctk.CTkFrame(self, width=196, fg_color="#151B17", corner_radius=0)
        rail.grid(row=0, column=0, sticky="nsew")
        rail.grid_propagate(False)
        rail.grid_columnconfigure(0, weight=1)
        rail.grid_rowconfigure(6, weight=1)
        self.label(rail, "h / g", 33, ACCENT, "bold").grid(row=0, padx=24, pady=(30, 0), sticky="w")
        self.label(rail, "HandGhost", 20, weight="bold").grid(
            row=1, padx=24, pady=(0, 2), sticky="w"
        )
        self.label(rail, "DESKTOP STUDIO", 10, MUTED).grid(row=2, padx=24, pady=(0, 40), sticky="w")
        self.nav = {}
        for row, name in enumerate(("Studio", "Preferences", "Gesture guide"), 3):
            button = self.button(
                rail, name, lambda value=name: self.show_page(value), anchor="w", width=160
            )
            button.grid(row=row, column=0, padx=16, pady=5, sticky="ew")
            self.nav[name] = button
        bottom = ctk.CTkFrame(rail, fg_color="transparent")
        bottom.grid(row=7, column=0, padx=24, pady=26, sticky="ew")
        self.label(bottom, "ON YOUR DEVICE", 10, ACCENT, "bold").pack(anchor="w")
        self.label(bottom, "Local processing.\nNo video uploads.", 12, MUTED, justify="left").pack(
            anchor="w", pady=(6, 16)
        )
        self.label(bottom, self.capability.label, 11, MUTED, wraplength=145, justify="left").pack(
            anchor="w"
        )

    def _build_header(self):
        header = ctk.CTkFrame(self.workspace, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        self.page_title = self.label(
            header, "Your hands. In control.", 28, weight="bold", anchor="w"
        )
        self.page_title.grid(row=0, column=0, sticky="w")
        self.status_badge = self.label(
            header, "  STANDBY  ", 11, ACCENT, "bold", fg_color=RAISED, corner_radius=8, height=30
        )
        self.status_badge.grid(row=0, column=1, padx=(16, 0), sticky="e")
        self.page_subtitle = self.label(
            header, "A little movement. A more natural desktop.", 13, MUTED, anchor="w"
        )
        self.page_subtitle.grid(row=1, column=0, columnspan=2, pady=(6, 0), sticky="w")
        self.notice = self.label(
            self.workspace,
            "Preview first. Enable desktop control when you’re ready.",
            12,
            MUTED,
            anchor="w",
        )
        self.notice.configure(wraplength=780, justify="left")
        self.notice.grid(row=1, column=0, pady=(20, 14), sticky="ew")

    def _build_studio(self):
        page = ctk.CTkFrame(self.workspace, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_columnconfigure(1, minsize=264)
        page.grid_rowconfigure(0, weight=1)
        left = ctk.CTkFrame(page, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(0, weight=1)
        self.preview = self.card(left)
        self.preview.grid(row=0, column=0, sticky="nsew")
        self.preview.grid_columnconfigure(0, weight=1)
        self.preview.grid_rowconfigure(1, weight=1)
        top = ctk.CTkFrame(self.preview, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=20, pady=16)
        self.label(top, "LIVE CANVAS", 11, MUTED, "bold").pack(side="left")
        self.preview_state = self.label(top, "Camera off", 11, MUTED)
        self.preview_state.pack(side="right")
        self.preview_calibrate_button = self.button(
            top, "Calibrate gaze", self.calibrate_eyes, width=140
        )
        self.video_area = ctk.CTkFrame(self.preview, fg_color="#111713", corner_radius=12)
        self.video_area.grid(row=1, column=0, sticky="nsew", padx=12)
        self.video_area.grid_columnconfigure(0, weight=1)
        self.video_area.grid_rowconfigure(0, weight=1)
        self.video_label = ctk.CTkLabel(self.video_area, text="", fg_color="transparent")
        self.video_label.grid(row=0, column=0, sticky="nsew")
        self.empty_state = ctk.CTkFrame(self.video_area, fg_color="transparent")
        self.empty_state.grid(row=0, column=0)
        self.label(self.empty_state, "(  /  )", 56, ACCENT).pack(pady=(0, 24))
        self.empty_title = self.label(
            self.empty_state, "Make room for a little magic.", 20, weight="bold"
        )
        self.empty_title.pack()
        self.empty_description = self.label(
            self.empty_state,
            "Start your camera to see your hands come to life.\nYour video stays right here, on this device.",
            13,
            MUTED,
            justify="center",
        )
        self.empty_description.pack(pady=(10, 24))
        self.button(self.empty_state, "Start camera", self.toggle_tracking, True, width=160).pack()
        footer = ctk.CTkFrame(self.preview, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=20, pady=14)
        self.gesture_label = self.label(footer, "Ready when you are", 12, MUTED)
        self.gesture_label.pack(side="left")
        self.label(footer, "LOCAL / PRIVATE", 10, ACCENT).pack(side="right")
        metrics = ctk.CTkFrame(left, fg_color="transparent")
        metrics.grid(row=1, column=0, sticky="ew", pady=(16, 0))
        self.metrics = {}
        self.metric_titles = {}
        for column, (key, title, value) in enumerate(
            (
                ("fps", "FRAME RATE", "— fps"),
                ("latency", "PROCESSING", "— ms"),
                ("hands", "HANDS", "0 / 2"),
            )
        ):
            metrics.grid_columnconfigure(column, weight=1, uniform="metrics")
            card = self.card(metrics)
            card.grid(row=0, column=column, sticky="ew", padx=(0, 10 if column < 2 else 0))
            heading = self.label(card, title, 10, MUTED, "bold")
            heading.pack(anchor="w", padx=16, pady=(15, 2))
            self.metric_titles[key] = heading
            label = self.label(card, value, 22, weight="bold")
            label.pack(anchor="w", padx=16, pady=(0, 15))
            self.metrics[key] = label
        controls = ctk.CTkScrollableFrame(
            page,
            width=244,
            fg_color=SURFACE,
            corner_radius=18,
            border_color=BORDER,
            border_width=1,
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=MUTED,
        )
        controls.grid(row=0, column=1, sticky="nsew")
        controls.grid_columnconfigure(0, weight=1)

        self.label(controls, "Session", 19, weight="bold").grid(
            row=0, column=0, sticky="w", padx=20, pady=(22, 3)
        )
        self.label(controls, "Find your flow.", 12, MUTED).grid(
            row=1, column=0, sticky="w", padx=20, pady=(0, 22)
        )
        camera_box = ctk.CTkFrame(controls, fg_color="transparent")
        camera_box.grid(row=2, column=0, sticky="ew", padx=20)
        self.mode_var = ctk.StringVar(
            value="Eyes"
            if self.settings_manager.get_setting("tracking_mode") == "eyes"
            else "Hands"
        )
        self.mode_selector = ctk.CTkSegmentedButton(
            camera_box,
            values=["Hands", "Eyes"],
            variable=self.mode_var,
            command=self._change_mode,
            selected_color="#38533B",
            selected_hover_color="#496C4D",
            unselected_color=RAISED,
            unselected_hover_color=BORDER,
            text_color=TEXT,
            height=36,
        )
        self.mode_selector.pack(fill="x", pady=(0, 16))
        self.label(camera_box, "CAMERA INDEX", 10, MUTED, "bold").pack(anchor="w", pady=(0, 8))
        cameras = CameraManager.list_available_cameras()
        self.camera_var = ctk.StringVar(
            value=str(self.settings_manager.get_setting("camera_index"))
        )
        self.camera_menu = ctk.CTkComboBox(
            camera_box,
            values=[str(i) for i in cameras] or ["0"],
            variable=self.camera_var,
            fg_color=BG,
            border_color=BORDER,
            button_color=RAISED,
            button_hover_color=BORDER,
            height=36,
        )
        self.camera_menu.pack(fill="x")
        self.camera_hint = self.label(
            camera_box,
            "No camera detected" if not cameras else "Choose a device or enter its index",
            11,
            MUTED,
            wraplength=218,
            justify="left",
        )
        self.camera_hint.pack(anchor="w", pady=(7, 12))
        self.start_stop_button = self.button(controls, "Start camera", self.toggle_tracking, True)
        self.start_stop_button.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 20))
        control_box = ctk.CTkFrame(controls, fg_color=RAISED, corner_radius=12)
        control_box.grid(row=4, column=0, sticky="ew", padx=14)
        self.controls_var = ctk.BooleanVar(value=False)
        self.control_switch = ctk.CTkSwitch(
            control_box,
            text="Desktop control",
            variable=self.controls_var,
            command=self._toggle_controls,
            progress_color=ACCENT,
            button_color=TEXT,
            font=ctk.CTkFont(size=13),
            onvalue=True,
            offvalue=False,
        )
        self.control_switch.pack(anchor="w", padx=14, pady=(15, 8))
        self.control_description = self.label(
            control_box, "Off · watch and practice first", 11, MUTED, wraplength=204, justify="left"
        )
        self.control_description.pack(anchor="w", padx=14, pady=(0, 15))
        if not self.capability.available:
            self.control_switch.configure(state="disabled")
            self.control_description.configure(text=self.capability.detail)
        self.eye_panel = ctk.CTkFrame(controls, fg_color="transparent")
        self.eye_panel.grid(row=5, column=0, sticky="ew", padx=20, pady=(20, 0))
        self.label(self.eye_panel, "EXPERIMENTAL GAZE", 10, ACCENT, "bold").pack(anchor="w")
        self.model_var = ctk.StringVar(
            value=MODELS[self.settings_manager.get_setting("eye_model")].label
        )
        self.model_selector = ctk.CTkOptionMenu(
            self.eye_panel,
            variable=self.model_var,
            values=[model.label for model in MODELS.values()],
            command=self._change_model,
            fg_color=RAISED,
            button_color=BORDER,
            button_hover_color="#405047",
            height=36,
        )
        self.model_selector.pack(fill="x", pady=(12, 6))
        self.model_status_label = self.label(
            self.eye_panel, "", 11, MUTED, wraplength=210, justify="left"
        )
        self.model_status_label.pack(anchor="w", pady=(0, 8))
        self.calibration_status = self.label(
            self.eye_panel, "Calibration needed", 11, MUTED, wraplength=215, justify="left"
        )
        self.calibration_status.pack(anchor="w", pady=(8, 10))
        self.calibrate_button = self.button(
            self.eye_panel, "Calibrate gaze · 9 points", self.calibrate_eyes
        )
        self.calibrate_button.pack(fill="x", pady=(0, 12))
        self.dwell_var = ctk.BooleanVar(value=False)
        self.dwell_switch = ctk.CTkSwitch(
            self.eye_panel,
            text="Dwell to click",
            variable=self.dwell_var,
            progress_color=ACCENT,
            command=self._toggle_dwell,
            font=ctk.CTkFont(size=13),
        )
        self.dwell_switch.pack(anchor="w", pady=(0, 8))
        self.dwell_progress = ctk.CTkProgressBar(
            self.eye_panel, progress_color=ACCENT, fg_color=BORDER, height=4
        )
        self.dwell_progress.set(0)
        self.dwell_progress.pack(fill="x", pady=(0, 10))
        self.label(
            self.eye_panel,
            "Hold your gaze to click. Look away\nto rearm. No blink clicks.",
            11,
            MUTED,
            justify="left",
        ).pack(anchor="w")
        quick = ctk.CTkFrame(controls, fg_color="transparent")
        quick.grid(row=6, column=0, sticky="ew", padx=20, pady=(24, 0))
        self.label(quick, "QUICK ADJUST", 10, MUTED, "bold").pack(anchor="w", pady=(0, 12))
        self._slider(quick, "mouse_sensitivity", "Pointer speed", 0.5, 8, 1)
        self._slider(quick, "smoothing_factor", "Smoothing", 0, 0.9, 2)
        safety = ctk.CTkFrame(controls, fg_color="transparent")
        safety.grid(row=8, column=0, sticky="ew", padx=20, pady=20)
        self.label(safety, "A QUICK WAY OUT", 10, ACCENT, "bold").pack(anchor="w")
        self.label(
            safety,
            "Esc pauses input in this window.\nMove the pointer to a screen\ncorner for the desktop fail-safe.",
            11,
            MUTED,
            justify="left",
        ).pack(anchor="w", pady=(8, 0))
        return page

    def _slider(self, parent, key, title, low, high, digits=0):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=(0, 5))
        self.label(row, title, 12).pack(side="left")
        value = self.settings_manager.get_setting(key)
        readout = self.label(row, f"{value:.{digits}f}", 12, ACCENT)
        readout.pack(side="right")

        def changed(number):
            self.settings_manager.set_setting(key, round(number, digits))
            readout.configure(text=f"{number:.{digits}f}")

        slider = ctk.CTkSlider(
            parent,
            from_=low,
            to=high,
            command=changed,
            progress_color=ACCENT,
            button_color=ACCENT,
            button_hover_color="#C6F1B5",
            fg_color=BORDER,
            height=16,
        )
        slider.set(value)
        slider.pack(fill="x", pady=(0, 20))
        return slider

    def _build_preferences(self):
        page = ctk.CTkScrollableFrame(self.workspace, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        models_card = self.card(page)
        models_card.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        self.label(models_card, "Gaze models", 20, weight="bold").pack(
            anchor="w", padx=24, pady=(22, 6)
        )
        self.label(
            models_card,
            "Select a model in Eyes mode. Only the selected model runs.\nMediaPipe is built in; optional models use local files. See docs/models.md.",
            13,
            MUTED,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 16))
        folder_row = ctk.CTkFrame(models_card, fg_color="transparent")
        folder_row.pack(fill="x", padx=24)
        self.models_path = ctk.StringVar(
            value=str(model_directory(self.settings_manager.snapshot()))
        )
        ctk.CTkEntry(
            folder_row, textvariable=self.models_path, fg_color=BG, border_color=BORDER
        ).pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.button(folder_row, "Browse", self._browse_models, width=100).pack(side="right")
        self.button(models_card, "Apply model folder", self._apply_model_directory, width=180).pack(
            anchor="w", padx=24, pady=(12, 18)
        )
        self.label(
            models_card,
            "L2CS: MIT code. GazeTR: noncommercial. iTracker: research only, no redistribution.\nCheck checkpoint terms before distributing any optional model.",
            11,
            MUTED,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 22))
        install_row = ctk.CTkFrame(models_card, fg_color="transparent")
        install_row.pack(fill="x", padx=24, pady=(0, 20))
        self.install_model_button = self.button(
            install_row, "Install selected model files", self.install_selected_model, width=220
        )
        self.install_model_button.pack(side="left", padx=(0, 12))
        self.button(
            install_row, "Import checkpoint…", self.import_model_checkpoint, width=180
        ).pack(side="left")
        tracking = self.card(page)
        tracking.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        self.label(tracking, "Make it feel like you", 20, weight="bold").pack(
            anchor="w", padx=24, pady=(22, 4)
        )
        self.label(
            tracking, "Adjustments apply live. Save to keep them for next time.", 13, MUTED
        ).pack(anchor="w", padx=24, pady=(0, 20))
        sliders = ctk.CTkFrame(tracking, fg_color="transparent")
        sliders.pack(fill="x", padx=24)
        self._slider(sliders, "pinch_threshold", "Pinch distance · % of palm width", 10, 70)
        self._slider(sliders, "target_fps", "Frame rate limit · lower uses less CPU", 10, 60)
        self._slider(sliders, "dwell_seconds", "Eye mode · dwell duration in seconds", 0.8, 3, 1)
        self.mirror_var = ctk.BooleanVar(value=self.settings_manager.get_setting("mirror_camera"))
        self.media_var = ctk.BooleanVar(
            value=self.settings_manager.get_setting("media_control_enabled")
        )
        for text, variable, key in (
            ("Mirror camera", self.mirror_var, "mirror_camera"),
            ("Enable media gestures", self.media_var, "media_control_enabled"),
        ):
            switch = ctk.CTkSwitch(
                tracking,
                text=text,
                variable=variable,
                progress_color=ACCENT,
                command=lambda k=key, var=variable: self._set_preference(k, var.get()),
            )
            switch.pack(anchor="w", padx=24, pady=(0, 18))
        mapping = self.card(page)
        mapping.grid(row=2, column=0, sticky="ew", pady=(0, 16))
        mapping.grid_columnconfigure(1, weight=1)
        self.label(mapping, "Your gesture map", 20, weight="bold").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=24, pady=(22, 4)
        )
        self.label(
            mapping, "One pose per action. Choose Unassigned to turn an action off.", 12, MUTED
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=24, pady=(0, 14))
        self.gesture_vars = {}
        for row, (action, title) in enumerate(ACTION_LABELS.items(), 2):
            self.label(mapping, title, 13).grid(row=row, column=0, sticky="w", padx=24, pady=7)
            var = ctk.StringVar(
                value=POSE_LABELS[self.settings_manager.get_setting("gestures").get(action, "None")]
            )
            self.gesture_vars[action] = var
            menu = ctk.CTkOptionMenu(
                mapping,
                variable=var,
                values=list(POSE_LABELS.values()),
                command=lambda value, name=action: self._remap(name, value),
                fg_color=RAISED,
                button_color=BORDER,
                button_hover_color="#405047",
                text_color=TEXT,
            )
            menu.grid(row=row, column=1, sticky="ew", padx=(12, 24), pady=7)
        self.label(mapping, "Media actions run once when you enter a pose.", 11, MUTED).grid(
            row=11, column=0, columnspan=2, sticky="w", padx=24, pady=(10, 22)
        )
        footer = ctk.CTkFrame(page, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", pady=(0, 16))
        self.button(footer, "Save preferences", self.save_and_apply_settings, True, width=180).pack(
            side="right"
        )
        self.label(footer, "Desktop control always starts off.", 12, MUTED).pack(side="left")
        return page

    def _build_guide(self):
        page = ctk.CTkScrollableFrame(self.workspace, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        instructions = [
            (
                "01",
                "Frame your hands",
                "Start the camera, sit in good light, and keep both hands in view.\nThe preview is mirrored, just like a mirror. Desktop control starts off.",
            ),
            (
                "02",
                "Move naturally",
                "Pinch your right thumb and index finger, then move your hand.\nRelease the pinch to reposition without moving the pointer.",
            ),
            (
                "03",
                "Click, hold, let go",
                "Pinch your left thumb and index finger to click. Hold it to drag.\nPinch your left thumb and middle finger for a right click.",
            ),
            (
                "04",
                "Find your scroll",
                "Pinch your right thumb and middle finger. Move that hand up or down\nto scroll. Release the pinch to stop.",
            ),
            (
                "05",
                "Try eye mode",
                "Choose Eyes, start the camera, then Calibrate gaze. Look at each dot\nand press Space. Keep your head steady. Calibration needs all nine points.\nEnable Desktop control to aim; Dwell to click is optional and starts off.",
            ),
            (
                "06",
                "Stay in control",
                "Enable Desktop control only when ready. Esc pauses input while this\nwindow is focused. A screen corner triggers the desktop fail-safe.\nLost hands, stopped tracking, and exit all release held mouse buttons.",
            ),
        ]
        for row, (number, title, detail) in enumerate(instructions):
            card = self.card(page)
            card.grid(row=row, column=0, sticky="ew", pady=(0, 12))
            self.label(card, number, 22, ACCENT, "bold").grid(
                row=0, column=0, rowspan=2, padx=24, pady=24, sticky="n"
            )
            self.label(card, title, 18, weight="bold").grid(
                row=0, column=1, sticky="w", pady=(20, 6)
            )
            self.label(card, detail, 13, MUTED, justify="left").grid(
                row=1, column=1, sticky="w", padx=(0, 24), pady=(0, 20)
            )
        return page

    def show_page(self, name):
        for page in self.pages.values():
            page.grid_forget()
        self.pages[name].grid(row=2, column=0, sticky="nsew")
        for label, button in self.nav.items():
            button.configure(
                fg_color=RAISED if label == name else "transparent",
                text_color=ACCENT if label == name else MUTED,
            )
        titles = {
            "Studio": ("Your hands. In control.", "A little movement. A more natural desktop."),
            "Preferences": (
                "Fine-tune your flow.",
                "Small adjustments that make all the difference.",
            ),
            "Gesture guide": (
                "A few simple moves.",
                "Start in preview mode. Get comfortable. Then take control.",
            ),
        }
        title, subtitle = titles[name]
        self.page_title.configure(text=title)
        self.page_subtitle.configure(text=subtitle)
        if name == "Studio" and self.settings_manager.get_setting("tracking_mode") == "eyes":
            self.page_title.configure(text="Your eyes. Set the direction.")
            self.page_subtitle.configure(
                text="Experimental webcam gaze. Calibrate, preview, then aim."
            )

    def install_selected_model(self, checkpoint=None):
        if self.worker.running:
            self._notify("Stop the camera before installing models.", error=True)
            return
        model = self.settings_manager.get_setting("eye_model")
        if model == "mediapipe":
            self._notify("MediaPipe is already included. Select another model in Eyes mode.")
            return
        if self._model_installer is not None and self._model_installer.is_alive():
            return
        directory = model_directory(self.settings_manager.snapshot())
        self.install_model_button.configure(text="Installing…", state="disabled")
        self._notify(
            "Downloading official assets with checksum verification. This may take a moment."
        )

        def install():
            from src.eye.model_setup import install as setup

            try:
                self._model_install_result = (setup(model, directory, checkpoint), False)
            except Exception as exc:
                self._model_install_result = (f"Model setup failed: {exc}", True)

        self._model_installer = threading.Thread(
            target=install, name="handghost-model-setup", daemon=True
        )
        self._model_installer.start()

    def import_model_checkpoint(self):
        if self.settings_manager.get_setting("eye_model") not in ("l2cs", "gazetr"):
            self._notify("Select L2CS-Net or GazeTR before importing a checkpoint.")
            return
        path = filedialog.askopenfilename(
            parent=self,
            title="Choose an official model state dictionary",
            filetypes=[("PyTorch weights", "*.pt *.pth *.pkl"), ("All files", "*")],
        )
        if path:
            self.settings_manager.set_setting("eye_calibration", None)
            self.install_selected_model(path)

    def _browse_models(self):
        folder = filedialog.askdirectory(parent=self, title="Choose the gaze model folder")
        if folder:
            self.models_path.set(folder)

    def _apply_model_directory(self):
        if self.worker.running:
            self._notify("Stop the camera before changing model files.", error=True)
            return
        self.settings_manager.set_setting("model_directory", self.models_path.get().strip())
        self.settings_manager.set_setting("eye_calibration", None)
        self.settings_manager.set_setting("eye_calibrations", {})
        self._session_state = None
        self._update_model_status()
        self._notify("Model folder applied. Save preferences to retain it.")

    def _update_model_status(self):
        settings = self.settings_manager.snapshot()
        available, reason = model_status(settings["eye_model"], model_directory(settings))
        self.model_status_label.configure(text=reason, text_color=MUTED if available else AMBER)
        return available

    def _change_model(self, label):
        if self.worker.running:
            return
        name = next(key for key, model in MODELS.items() if model.label == label)
        self.pause_controls()
        settings = self.settings_manager.snapshot()
        cached = settings["eye_calibrations"]
        if settings["eye_calibration"] is not None:
            cached[settings["eye_model"]] = settings["eye_calibration"]
        self.settings_manager.set_setting("eye_calibrations", cached)
        self.settings_manager.set_setting("eye_model", name)
        self.model_var.set(label)
        self.settings_manager.set_setting("eye_calibration", cached.get(name))
        self._session_state = None
        self._update_model_status()
        self._notify("Model changed. Calibrate this model before enabling input.")

    def _set_preference(self, key, value):
        if key == "mirror_camera":
            self.pause_controls()
            self.settings_manager.set_setting("eye_calibration", None)
        self.settings_manager.set_setting(key, value)

    def _change_mode(self, value):
        if self.worker.running:
            return
        self.pause_controls()
        self.settings_manager.set_setting("tracking_mode", "eyes" if value == "Eyes" else "hands")
        self._refresh_mode()

    def _refresh_mode(self):
        eyes = self.settings_manager.get_setting("tracking_mode") == "eyes"
        if eyes:
            self.eye_panel.grid()
            self.preview_calibrate_button.pack(side="right", padx=12)
        else:
            self.eye_panel.grid_remove()
            self.preview_calibrate_button.pack_forget()
        self.empty_title.configure(
            text="A new way to see your desktop." if eyes else "Make room for a little magic."
        )
        self.empty_description.configure(
            text=(
                "Start the camera, choose a model, then calibrate your gaze.\nYour video stays right here, on this device."
                if eyes
                else "Start your camera to see your hands come to life.\nYour video stays right here, on this device."
            )
        )
        self.metric_titles["hands"].configure(text="FACE" if eyes else "HANDS")
        self.metrics["hands"].configure(text="0 / 1" if eyes else "0 / 2")
        self.show_page("Studio")
        self._update_model_status()

    def _has_calibration(self):
        try:
            data = self.settings_manager.get_setting("eye_calibration")
            model = GazeCalibration(data)
            return (
                model.screen == self.worker.screen
                and data.get("camera_index") == self.settings_manager.get_setting("camera_index")
                and data.get("mirror") == self.settings_manager.get_setting("mirror_camera")
                and data.get("model", "mediapipe") == self.settings_manager.get_setting("eye_model")
            )
        except (ValueError, TypeError):
            return False

    def _toggle_dwell(self):
        self.settings_manager.set_setting("dwell_click_enabled", self.dwell_var.get())

    def calibrate_eyes(self):
        if self._calibration_window is not None and self._calibration_window.winfo_exists():
            self._calibration_window.lift()
            return
        if not self.worker.running:
            self._notify("Start the camera in Eyes mode before calibrating.", error=True)
            return
        self.pause_controls()
        self.dwell_var.set(False)
        self.settings_manager.set_setting("dwell_click_enabled", False)
        self._calibration_window = EyeCalibrationWindow(
            self, lambda: self._eye_features, self._save_calibration
        )

    def _save_calibration(self, data):
        data["camera_index"] = self.settings_manager.get_setting("camera_index")
        data["mirror"] = self.settings_manager.get_setting("mirror_camera")
        data["model"] = self.settings_manager.get_setting("eye_model")
        self.settings_manager.set_setting("eye_calibration", data)
        self._notify(
            f"Calibration complete · estimated error {data['error']:.0%} of screen. Test aiming before enabling clicks."
        )
        try:
            self.settings_manager.save_settings()
        except OSError:
            self._notify(
                "Calibration works for this session. Save preferences to retain it.", error=True
            )

    def _remap(self, action, label):
        primitive = next(key for key, value in POSE_LABELS.items() if value == label)
        mapping = self.settings_manager.get_setting("gestures")
        if primitive != "None" and any(
            value == primitive for key, value in mapping.items() if key != action
        ):
            self.gesture_vars[action].set(POSE_LABELS[mapping.get(action, "None")])
            self._notify("That pose is already assigned. Unassign it first.", error=True)
            return
        mapping[action] = primitive
        self.settings_manager.set_setting("gestures", mapping)

    def _notify(self, message, error=False):
        self._message = message
        self._message_until = time.monotonic() + 6
        self._notice_key = None
        self.notice.configure(text=message, text_color=AMBER if error else ACCENT)

    def _toggle_controls(self):
        enabled = (
            self.controls_var.get()
            and self.worker.running
            and self.capability.available
            and (
                self.settings_manager.get_setting("tracking_mode") != "eyes"
                or self._has_calibration()
            )
        )
        self.controls_var.set(enabled)
        self.settings_manager.set_setting("controls_enabled", enabled)
        if not enabled:
            self.worker.pause()
            self._notify("Desktop control paused. Preview stays on.")

    def pause_controls(self, event=None):
        self.controls_var.set(False)
        self.worker.pause()
        self._notify("Desktop control paused.")

    def toggle_tracking(self):
        if self.worker.running:
            self._stop_requested = True
            self.worker.stop()
            self.start_stop_button.configure(text="Stopping…", state="disabled")
            return
        try:
            index = int(self.camera_var.get())
            if not 0 <= index <= 99:
                raise ValueError
        except ValueError:
            self._notify("Enter a camera index between 0 and 99.", error=True)
            return
        if index != self.settings_manager.get_setting("camera_index"):
            self.settings_manager.set_setting("eye_calibration", None)
        self.settings_manager.set_setting("camera_index", index)
        if (
            self.settings_manager.get_setting("tracking_mode") == "eyes"
            and not self._update_model_status()
        ):
            self._notify(
                "Selected model needs setup. Open Preferences → Gaze models; see docs/models.md.",
                error=True,
            )
            return
        self.pause_controls()
        self._stop_requested = False
        self.worker.start()
        self.start_stop_button.configure(text="Stop camera")
        self.camera_menu.configure(state="disabled")
        self.preview_state.configure(text="Connecting…", text_color=ACCENT)
        self._notify("Connecting to camera…")

    def save_and_apply_settings(self):
        try:
            self.settings_manager.save_settings()
            self._notify("Preferences saved. Your next session will feel right at home.")
        except OSError as exc:
            self._notify(f"Could not save preferences: {exc}", error=True)

    def _draw_frame(self):
        if self._last_frame is None:
            return
        width = max(1, self.video_area.winfo_width() - 12)
        height = max(1, self.video_area.winfo_height() - 12)
        source = self._last_frame
        scale = min(width / source.shape[1], height / source.shape[0])
        size = (max(1, int(source.shape[1] * scale)), max(1, int(source.shape[0] * scale)))
        image = Image.fromarray(source)
        if image.size != size:
            image = image.resize(size, Image.Resampling.BILINEAR)
        self._last_photo = ctk.CTkImage(light_image=image, dark_image=image, size=size)
        self.video_label.configure(image=self._last_photo)
        self._last_size = (width, height)
        self.empty_state.grid_remove()

    def _tick(self):
        if self._closing:
            return
        if self._model_install_result is not None:
            message, error = self._model_install_result
            self._model_install_result = None
            self.install_model_button.configure(text="Install selected model files", state="normal")
            self._update_model_status()
            self._notify(message, error=error)
        packet = self.worker.take_latest()
        if packet is not None:
            if packet.image is not None:
                self._last_frame = packet.image
                if self.studio.winfo_ismapped():
                    self._draw_frame()
                eye_mode = self.settings_manager.get_setting("tracking_mode") == "eyes"
                if time.monotonic() - self._last_metrics >= 0.2:
                    self.metrics["fps"].configure(text=f"{packet.fps:.0f} fps")
                    self.metrics["latency"].configure(text=f"{packet.latency_ms:.0f} ms")
                    self.metrics["hands"].configure(text=f"{packet.hands} / {1 if eye_mode else 2}")
                    self.gesture_label.configure(text=packet.gesture.capitalize()[:62])
                    self._last_metrics = time.monotonic()
                self._eye_features = (
                    packet.eye_features if packet.eyes_open else None,
                    time.monotonic(),
                )
                self.dwell_progress.set(packet.dwell_progress)
                self.preview_state.configure(
                    text="Live · mirrored" if self.mirror_var.get() else "Live", text_color=ACCENT
                )
            if packet.error and packet.error != self._message:
                self._notify(packet.error, error=True)
        running = self.worker.running
        enabled = self.settings_manager.get_setting("controls_enabled")
        eye_mode = self.settings_manager.get_setting("tracking_mode") == "eyes"
        calibrated = self._has_calibration() if eye_mode else True
        state = (running, enabled, eye_mode, calibrated, self._stop_requested)
        if state != self._session_state:
            self._session_state = state
            self.controls_var.set(enabled)
            self.status_badge.configure(
                text="  IN CONTROL  " if enabled else "  PREVIEW  " if running else "  STANDBY  ",
                text_color=ACCENT if enabled else MUTED,
            )
            self.preview_calibrate_button.configure(state="normal" if running else "disabled")
            self.mode_selector.configure(state="disabled" if running else "normal")
            self.model_selector.configure(state="disabled" if running else "normal")
            self.calibration_status.configure(
                text="Calibrated · recalibrate if you move"
                if calibrated
                else "Start camera, then calibrate your gaze."
            )
            self.dwell_switch.configure(state="normal" if running and calibrated else "disabled")
            if not running:
                self.dwell_var.set(False)
                self.settings_manager.set_setting("dwell_click_enabled", False)
                self.dwell_progress.set(0)
                self._eye_features = (None, 0)
            if self.capability.available:
                self.control_switch.configure(
                    state="normal"
                    if running and not self._stop_requested and calibrated
                    else "disabled"
                )
                self.control_description.configure(
                    text="On · gestures move your desktop"
                    if enabled
                    else "Off · watch and practice first"
                )
            if not running:
                self.start_stop_button.configure(text="Start camera", state="normal")
                self.camera_menu.configure(state="normal")
                self.preview_state.configure(text="Camera off", text_color=MUTED)
                self.video_label.configure(image=None)
                self._last_frame = self._last_photo = None
                self.empty_state.grid()
                self.gesture_label.configure(text="Ready when you are")
                for key, value in (
                    ("fps", "— fps"),
                    ("latency", "— ms"),
                    ("hands", "0 / 1" if eye_mode else "0 / 2"),
                ):
                    self.metrics[key].configure(text=value)
        notice_key = (self.worker.error, self.capability.available)
        if time.monotonic() > self._message_until and self._notice_key != notice_key:
            self._notice_key = notice_key
            self.notice.configure(
                text=self.worker.error
                or (
                    "Preview first. Enable desktop control when you’re ready."
                    if self.capability.available
                    else self.capability.detail
                ),
                text_color=AMBER if self.worker.error else MUTED,
            )
        self.after(33 if running else 100, self._tick)

    def on_closing(self):
        if self._closing:
            return
        self._closing = True
        for callback in self.tk.call("after", "info"):
            try:
                self.after_cancel(callback)
            except Exception:
                pass
        self.worker.stop()
        self.withdraw()
        self._wait_for_worker(time.monotonic() + 3)

    def _wait_for_worker(self, deadline):
        if self.worker.running and time.monotonic() < deadline:
            self.after(50, lambda: self._wait_for_worker(deadline))
        else:
            self.destroy()

    def run(self):
        self.mainloop()
