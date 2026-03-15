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
        self._starting = True
        threading.Thread(target=self._start_preview_worker, daemon=True).start()

    def _start_preview_worker(self):
        try:
            self.camera = Picamera2()
            cfg = self.camera.create_preview_configuration(
                main={
                    'size':   (self.PREVIEW_WIDTH, self.PREVIEW_HEIGHT),
                    'format': 'RGB888'          # RGB888 = RGB — no flip needed
                },
                buffer_count=4
            )
            self.camera.configure(cfg)
            self.camera.start()
            self.preview_active = True
            print("[CAMERA] Preview started")
        except Exception as e:
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
            self._starting       = False   # ← clear starting flag too
            print("[CAMERA] Preview stopped")

    def get_preview_texture(self):
        if not HAS_CAMERA or not self.preview_active or self.camera is None:
            return None
        try:
            with self._lock:
                frame   = self.camera.capture_array("main")
                h, w, _ = frame.shape
                # RGB888 is already RGB — just flip vertically for Kivy origin
                flipped = frame[::-1, :, :].copy()
                texture = Texture.create(size=(w, h), colorfmt='rgb')
                texture.blit_buffer(
                    flipped.tobytes(),
                    colorfmt='rgb', bufferfmt='ubyte'
                )
                self.current_texture = texture
                return texture
        except Exception as e:
            print(f"[CAMERA] Frame error: {e}")
            return self.current_texture     # last good frame on transient error

    def is_preview_ready(self):
        """Capture screen polls this to know when to start the preview clock."""
        return self.preview_active

    # ── Capture ────────────────────────────────────────────────────────────────

    def capture_image(self):
        """
        Capture a full-res still. Preview must already be stopped by the
        caller (capture_screen._trigger_capture calls stop_preview first).
        Does NOT restart preview — screen lifecycle manages that.
        """
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
            self.camera = Picamera2()
            cfg = self.camera.create_still_configuration(
                main={
                    'size':   (self.CAPTURE_WIDTH, self.CAPTURE_HEIGHT),
                    'format': 'RGB888'
                }
            )
            self.camera.configure(cfg)
            self.camera.start()
            time.sleep(2)               # auto-exposure settle
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
            # ↑ No preview restart here — capture_screen.on_enter handles it
            #   when the screen returns after CNN result

    # ── Cleanup ────────────────────────────────────────────────────────────────

    def cleanup(self):
        self.stop_preview()
        self._initialized = False
        print("[CAMERA] Cleanup done")
