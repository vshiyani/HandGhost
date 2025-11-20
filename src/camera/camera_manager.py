import cv2
from src.utils.logger import Logger

class CameraManager:
    """
    Manages the webcam.
    """
    def __init__(self, camera_index=0):
        self.logger = Logger.get_logger(__name__)
        self.camera_index = camera_index
        self.cap = None

    def get_camera(self, width=1280, height=720, fps=30):
        """
        Initializes and returns the camera capture object, attempting to set resolution and FPS.
        """
        if self.cap is not None:
            self.release_camera()

        self.cap = cv2.VideoCapture(self.camera_index)

        if not self.cap.isOpened():
            self.logger.error(f"Failed to open camera with index {self.camera_index}.")
            return None

        # Attempt to set resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        if actual_width != width or actual_height != height:
            self.logger.warning(f"Requested resolution {width}x{height} not supported. "
                                f"Actual resolution: {int(actual_width)}x{int(actual_height)}")
        else:
            self.logger.info(f"Camera resolution set to {int(actual_width)}x{int(actual_height)}.")

        # Attempt to set FPS
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
        if actual_fps != fps:
            self.logger.warning(f"Requested FPS {fps} not supported. Actual FPS: {int(actual_fps)}")
        else:
            self.logger.info(f"Camera FPS set to {int(actual_fps)}.")

        return self.cap

    def release_camera(self):
        """
        Releases the camera capture object.
        """
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    @staticmethod
    def list_available_cameras():
        """
        Lists available camera indices.

        Returns:
            A list of integers representing the indices of available cameras.
        """
        available_cameras = []
        # Try opening camera indices from 0 up to a reasonable limit
        for i in range(10): # Check up to 10 cameras
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available_cameras.append(i)
                cap.release()
            else:
                # If a camera index cannot be opened, it's likely no more cameras are available
                # or there's a permission issue, but for simple detection, we can break
                # if the first few fail. However, iterating all 10 is safer.
                pass
        return available_cameras
