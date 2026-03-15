import os
import time
import threading
from datetime import datetime

try:
    from picamera2 import Picamera2
    HAS_CAMERA = True
except ImportError:
    HAS_CAMERA = False
    print("[CAMERA] picamera2 not available")

from kivy.graphics.texture import Texture


class CameraManager:

    PREVIEW_WIDTH  = 240
    PREVIEW_HEIGHT = 180
    CAPTURE_WIDTH  = 2592
    CAPTURE_HEIGHT = 1944

    def __init__(self):
        self.camera          = None
        self.preview_active  = False
        self.current_texture = None
        self._lock           = threading.Lock()
        self._initialized    = False
        self._capturing      = False
        self._starting       = False
        self._last_error     = None   # stores last exception for debugging

    def initialize(self):
        if not HAS_CAMERA:
            print("[CAMERA] Simulation mode (picamera2 not found)")
            return
        self._initialized = True
        print("[CAMERA] Initialized")

    # ── Preview ────────────────────────────────────────────────────────────────

    def start_preview(self):
        if not HAS_CAMERA or not self._initialized:
            return
        if self.preview_active or self._starting:
            print("[CAMERA] Preview already active/starting — skipped")
            return
        self._starting    = True
        self._last_error  = None
        threading.Thread(target=self._start_preview_worker, daemon=True).start()

    def _start_preview_worker(self):
        try:
            time.sleep(1.0)      # give kernel time to release camera fd between sessions
            self.camera = Picamera2()
            cfg = self.camera.create_preview_configuration(
                main={
                    'size':   (self.PREVIEW_WIDTH, self.PREVIEW_HEIGHT),
                    'format': 'RGB888'
                },
                buffer_count=4
            )
            self.camera.configure(cfg)
            self.camera.start()
            self.preview_active = True
            print("[CAMERA] Preview started")
        except Exception as e:
            self._last_error = e
            print(f"[CAMERA] Preview start error: {e}")
            self.preview_active = False
            try:
                if self.camera:
                    self.camera.close()
            except Exception:
                pass
            self.camera = None
        finally:
            self._starting = False

    def stop_preview(self):
        if not HAS_CAMERA or self.camera is None:
            return
        try:
            if self.preview_active:
                self.camera.stop()
            self.camera.close()
        except Exception as e:
            print(f"[CAMERA] Preview stop error: {e}")
        finally:
            self.camera          = None
            self.preview_active  = False
            self.current_texture = None
            self._starting       = False
            print("[CAMERA] Preview stopped")

    def get_preview_texture(self):
        if not HAS_CAMERA or not self.preview_active or self.camera is None:
            return None
        try:
            with self._lock:
                frame     = self.camera.capture_array("main")
                h, w, _   = frame.shape
                frame_rgb = frame[:, :, ::-1].copy()   # BGR → RGB
                flipped   = frame_rgb[::-1, :, :]      # vertical flip for Kivy origin
                texture   = Texture.create(size=(w, h), colorfmt='bgr')
                texture.blit_buffer(
                    flipped.tobytes(),
                    colorfmt='bgr', bufferfmt='ubyte'
                )
                self.current_texture = texture
                return texture
        except Exception as e:
            print(f"[CAMERA] Frame error: {e}")
            return self.current_texture

    def is_preview_ready(self):
        return self.preview_active

    def get_last_error(self):
        return self._last_error

    # ── Capture ────────────────────────────────────────────────────────────────

    def capture_image(self):
        if self._capturing:
            print("[CAMERA] Capture already in progress")
            return None

        self._capturing = True

        timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        captures_dir = os.path.join(base_dir, 'captures')
        os.makedirs(captures_dir, exist_ok=True)
        filename = os.path.join(captures_dir, f"capture_{timestamp}.jpg")

        try:
            time.sleep(0.5)      # ensure preview fully released before reopening
            self.camera = Picamera2()
            cfg = self.camera.create_still_configuration(
                main={
                    'size':   (self.CAPTURE_WIDTH, self.CAPTURE_HEIGHT),
                    'format': 'RGB888'
                }
            )
            self.camera.configure(cfg)
            self.camera.start()
            time.sleep(2)        # auto-exposure settle
            self.camera.capture_file(filename)
            self.camera.stop()
            self.camera.close()
            self.camera = None
            print(f"[CAMERA] Captured: {filename}")
            return filename

        except Exception as e:
            print(f"[CAMERA] Capture error: {e}")
            try:
                if self.camera:
                    self.camera.stop()
                    self.camera.close()
            except Exception:
                pass
            self.camera = None
            return None

        finally:
            self._capturing = False

    # ── Cleanup ────────────────────────────────────────────────────────────────

    def cleanup(self):
        self.stop_preview()
        self._initialized = False
        print("[CAMERA] Cleanup done")

