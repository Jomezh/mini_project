# hardware/camera.py
from hardware.platform import is_pi
import time

class Camera:
    def __init__(self):
        if is_pi():
            self._init_real()
        else:
            self._init_mock()

    def _init_real(self):
        # picamera2 init later
        self.ready = True
        print("Camera initialized (real)")

    def _init_mock(self):
        self.ready = True
        self.mock_image = "assets/sample.jpg"
        print("[MOCK] Camera initialized")

    def preview(self):
        """
        Return preview frame (path or bytes).
        """
        if is_pi():
            return self._real_preview()
        else:
            return self.mock_image

    def capture(self):
        """
        Capture full-resolution image.
        """
        if is_pi():
            return self._real_capture()
        else:
            return {
                "path": self.mock_image,
                "timestamp": time.time()
            }

    def _real_preview(self):
        # low-res capture later
        pass

    def _real_capture(self):
        # full capture later
        pass
