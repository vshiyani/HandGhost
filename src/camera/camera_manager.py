"""Camera ownership stays on the tracking worker; enumeration never probes Linux devices."""

import sys
from glob import glob
from pathlib import Path

import cv2


class CameraManager:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None

    def get_camera(self, width=640, height=480, fps=30):
        self.release_camera()
        backend = cv2.CAP_V4L2 if sys.platform.startswith("linux") else cv2.CAP_ANY
        self.cap = cv2.VideoCapture(self.camera_index, backend)
        if not self.cap.isOpened():
            self.release_camera()
            return None
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return self.cap

    def release_camera(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    @staticmethod
    def list_available_cameras():
        if sys.platform.startswith("linux"):
            return sorted(
                int(Path(path).name[5:])
                for path in glob("/dev/video[0-9]*")
                if Path(path).name[5:].isdigit()
            )
        # Avoid blocking GUI startup by opening a series of devices. The UI also accepts an index.
        return [0, 1, 2, 3]
