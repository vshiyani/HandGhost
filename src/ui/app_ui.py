import customtkinter as ctk
from PIL import Image
import cv2
import json

from src.utils.settings_manager import SettingsManager
from src.camera.camera_manager import CameraManager
from src.detection.hand_detector import HandDetector
from src.gesture.gesture_recognizer import GestureRecognizer
from src.rendering.ghost_hand_renderer import GhostHandRenderer
from src.interaction.os_interaction import OSInteraction
from src.utils.logger import Logger

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class HandGhostGUI(ctk.CTk):
    def __init__(self, settings_manager: SettingsManager):
        super().__init__()

        self.logger = Logger.get_logger()
        self.settings_manager = settings_manager
        self.title("HandGhost")
        self.geometry("1400x800")

        # --- Data ---
        self.cap = None
        self.camera_width = 1280
        self.camera_height = 720
        self.is_tracking = False

        # --- Initialize Components ---
        self.camera_manager = CameraManager()
        self.hand_detector = HandDetector()
        self.gesture_recognizer = GestureRecognizer(self.settings_manager)
        self.renderer = GhostHandRenderer()
        self.os_interaction = OSInteraction(self.settings_manager) # Pass settings_manager
        self.apply_settings() # Apply loaded settings to components

        # --- Configure Grid Layout ---
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Video Frame ---
        self.video_frame = ctk.CTkFrame(self, corner_radius=0)
        self.video_frame.grid(row=0, column=0, sticky="nsew")
        self.video_label = ctk.CTkLabel(self.video_frame, text="")
        self.video_label.pack(fill="both", expand=True)

        # --- Settings Panel ---
        self._create_settings_panel()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _create_settings_panel(self):
        # Main Settings Frame
        self.settings_panel = ctk.CTkFrame(self)
        self.settings_panel.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.settings_panel.grid_columnconfigure(0, weight=1)
        
        settings_title = ctk.CTkLabel(self.settings_panel, text="HandGhost Settings", font=ctk.CTkFont(size=24, weight="bold"))
        settings_title.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        # Scrollable Frame for all settings
        scrollable_frame = ctk.CTkScrollableFrame(self.settings_panel, label_text="Configuration")
        scrollable_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        scrollable_frame.grid_columnconfigure(0, weight=1)

        # --- General Settings ---
        general_frame = ctk.CTkFrame(scrollable_frame)
        general_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        general_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(general_frame, text="Camera:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        available_cameras = self.camera_manager.list_available_cameras()
        self.camera_var = ctk.StringVar(value=str(self.settings_manager.get_setting("camera_index")))
        ctk.CTkOptionMenu(general_frame, variable=self.camera_var, values=[str(i) for i in available_cameras] if available_cameras else ["None"]).grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(general_frame, text="Pinch Threshold").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.pinch_slider = ctk.CTkSlider(general_frame, from_=10, to=80, number_of_steps=70)
        self.pinch_slider.set(self.settings_manager.get_setting("pinch_threshold"))
        self.pinch_slider.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(general_frame, text="Mouse Sensitivity").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.sensitivity_slider = ctk.CTkSlider(general_frame, from_=1.0, to=10.0, number_of_steps=90)
        self.sensitivity_slider.set(self.settings_manager.get_setting("mouse_sensitivity"))
        self.sensitivity_slider.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
        self.media_control_var = ctk.BooleanVar(value=self.settings_manager.get_setting("media_control_enabled"))
        ctk.CTkCheckBox(general_frame, text="Enable Media Controls", variable=self.media_control_var).grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="w")


        # --- Gesture Mapping ---
        gesture_frame = ctk.CTkFrame(scrollable_frame)
        gesture_frame.grid(row=1, column=0, padx=5, pady=10, sticky="ew")
        gesture_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(gesture_frame, text="Gesture Mapping", font=ctk.CTkFont(weight="bold")).grid(row=0, columnspan=2, padx=10, pady=5)
        
        self.gesture_vars = {}
        row_num = 1
        for action in self.settings_manager.get_setting("gestures"):
            ctk.CTkLabel(gesture_frame, text=action.replace("_", " ").title() + ":").grid(row=row_num, column=0, padx=10, pady=5, sticky="w")
            var = ctk.StringVar(value=self.settings_manager.get_setting("gestures")[action])
            self.gesture_vars[action] = var
            menu = ctk.CTkOptionMenu(gesture_frame, variable=var, values=GestureRecognizer.PRIMITIVE_GESTURES)
            menu.grid(row=row_num, column=1, padx=10, pady=5, sticky="ew")
            row_num += 1
            
        # --- Control Buttons ---
        self.start_stop_button = ctk.CTkButton(self.settings_panel, text="Start Tracking", command=self.toggle_tracking, height=40)
        self.start_stop_button.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        self.save_button = ctk.CTkButton(self.settings_panel, text="Save Settings", command=self.save_and_apply_settings, height=40)
        self.save_button.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

    def save_and_apply_settings(self):
        self.settings_manager.set_setting("camera_index", int(self.camera_var.get()))
        self.settings_manager.set_setting("pinch_threshold", self.pinch_slider.get())
        self.settings_manager.set_setting("mouse_sensitivity", self.sensitivity_slider.get())
        self.settings_manager.set_setting("media_control_enabled", self.media_control_var.get())
        
        new_gestures = {action: var.get() for action, var in self.gesture_vars.items()}
        self.settings_manager.set_setting("gestures", new_gestures)
        
        self.settings_manager.save_settings()
        self.apply_settings()
        self.logger.info("Settings saved and applied.")

    def apply_settings(self):
        """Applies the current settings from the SettingsManager to all components."""
        self.os_interaction.set_sensitivity(self.settings_manager.get_setting("mouse_sensitivity"))
        # self.gesture_recognizer.set_pinch_threshold(self.settings_manager.get_setting("pinch_threshold"))
        # The gesture recognizer now gets settings on the fly, so no explicit call is needed here
        # unless we add more settings that need to be explicitly passed.
        self.logger.info("Settings applied to components.")


    def toggle_tracking(self):
        if self.is_tracking:
            self.is_tracking = False
            self.start_stop_button.configure(text="Start Tracking")
            if self.cap:
                self.camera_manager.release_camera()
                self.cap = None
            self.video_label.configure(image=None)
            self.logger.info("Tracking stopped.")
        else:
            if self._start_camera():
                self.is_tracking = True
                self.start_stop_button.configure(text="Stop Tracking")
                self.logger.info("Tracking started.")
                self._update_frame()

    def _start_camera(self):
        selected_camera_index = int(self.camera_var.get())
        self.settings_manager.set_setting("camera_index", selected_camera_index)
        self.camera_manager.camera_index = selected_camera_index
        
        configs_to_try = [(640, 480, 30), (1280, 720, 30)]
        for w, h, f in configs_to_try:
            self.cap, self.camera_width, self.camera_height = self.try_initialize_camera(w, h, f)
            if self.cap:
                self.os_interaction.camera_width = self.camera_width
                self.os_interaction.camera_height = self.camera_height
                return True
        self.logger.error("Failed to open camera with any configuration.")
        return False

    def try_initialize_camera(self, width, height, fps):
        cap = self.camera_manager.get_camera(width=width, height=height, fps=fps)
        if cap and cap.isOpened():
            actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.logger.info(f"Camera initialized at {actual_width}x{actual_height}.")
            return cap, actual_width, actual_height
        return None, None, None

    def _update_frame(self):
        if not self.is_tracking or not self.cap or not self.cap.isOpened():
            return

        success, frame = self.cap.read()
        if not success:
            self.after(20, self._update_frame)
            return

        frame = cv2.flip(frame, 1)

        all_hands_landmarks, all_hands_handedness = self.hand_detector.detect(frame)
        gestures = self.gesture_recognizer.recognize(all_hands_landmarks, all_hands_handedness, frame)
        for gesture in gestures:
            self.os_interaction.perform_action(gesture)
        
        frame = self.renderer.draw(frame, all_hands_landmarks, gestures)

        # Convert image for display
        cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(cv2image)
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(self.camera_width, self.camera_height))
        
        self.video_label.configure(image=ctk_img)

        self.after(10, self._update_frame)
    
    def on_closing(self):
        self.is_tracking = False
        if self.cap:
            self.camera_manager.release_camera()
        self.destroy()

    def run(self):
        self.mainloop()
