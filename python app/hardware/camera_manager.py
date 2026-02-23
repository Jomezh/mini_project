import os
import time
import threading
import subprocess
from datetime import datetime

try:
    from picamera2 import Picamera2
    HAS_CAMERA = True
except ImportError:
    HAS_CAMERA = False
    print("[CAMERA] picamera2 not available")

from kivy.graphics.texture import Texture


class CameraManager:
    """Raspberry Pi Camera (OV5647 / CSI) via picamera2"""

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
        self._starting       = False  # Atomic guard — FadeTransition fires on_enter twice

    def _force_reset(self):
        """Kill stale /dev/video0 handle from previous run."""
        try:
            subprocess.run(["sudo", "fuser", "-k", "/dev/video0"],
                           capture_output=True)
            time.sleep(1.5)
        except Exception as e:
            print(f"[CAMERA] Reset warning: {e}")

    def initialize(self):
        """
        Lightweight init only — marks hardware available.
        Picamera2() is created in start_preview()/capture_image()
        so there is zero gap between open and start (matches working test).
        """
        if not HAS_CAMERA:
            print("[CAMERA] Simulation mode (picamera2 not found)")
            return
        self._initialized = True
        print("[CAMERA] Initialized")

    # ── Preview ────────────────────────────────────────

    def start_preview(self):
        if not HAS_CAMERA or not self._initialized:
            return
        if self.preview_active or self._starting:
            print("[CAMERA] Preview already active/starting — skipped")
            return

        self._starting = True
        try:
            # _force_reset + Picamera2() + configure + start in one atomic sequence
            # This mirrors camera_preview.py which worked — no gap between open and start
            self._force_reset()
            self.camera = Picamera2()

            cfg = self.camera.create_preview_configuration(
                main={'size': (self.PREVIEW_WIDTH, self.PREVIEW_HEIGHT),
                      'format': 'RGB888'},
                buffer_count=4   # 4 buffers — matches working standalone test
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
            self.camera          = None
            self.preview_active  = False
            self.current_texture = None
            print("[CAMERA] Preview stopped")
        except Exception as e:
            print(f"[CAMERA] Preview stop error: {e}")
            self.camera         = None
            self.preview_active = False

    def get_preview_texture(self):
        if not HAS_CAMERA or not self.preview_active or self.camera is None:
            return None
        try:
            with self._lock:
                frame     = self.camera.capture_array("main")
                h, w, _   = frame.shape
                frame_rgb = frame[:, :, ::-1].copy()  # BGR → RGB
                flipped   = frame_rgb[::-1, :, :]     # Kivy bottom-left origin

                texture = Texture.create(size=(w, h), colorfmt='rgb')
                texture.blit_buffer(
                    flipped.tobytes(),
                    colorfmt='rgb', bufferfmt='ubyte'
                )
                self.current_texture = texture
                return texture
        except Exception as e:
            print(f"[CAMERA] Frame error: {e}")
            return self.current_texture

    # ── Capture ────────────────────────────────────────

    def capture_image(self):
        """Capture full-resolution still. Returns file path or None."""
        if self._capturing:
            print("[CAMERA] Capture already in progress")
            return None

        self._capturing = True

        timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        captures_dir = os.path.join(base_dir, 'captures')
        os.makedirs(captures_dir, exist_ok=True)
        filename     = os.path.join(captures_dir, f"capture_{timestamp}.jpg")

        was_previewing = self.preview_active

        try:
            if was_previewing:
                self.stop_preview()      # Also closes camera + nullifies self.camera
                time.sleep(1.5)          # i2c bus release

            # Create fresh Picamera2 atomically right before capture
            self._force_reset()
            self.camera = Picamera2()

            cfg = self.camera.create_still_configuration(
                main={'size': (self.CAPTURE_WIDTH, self.CAPTURE_HEIGHT),
                      'format': 'RGB888'}
            )
            self.camera.configure(cfg)
            self.camera.start()
            time.sleep(2)                # Auto-exposure settle
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
            if was_previewing:
                try:
                    self.start_preview()
                except Exception as ex:
                    print(f"[CAMERA] Preview restart failed: {ex}")

    # ── Cleanup ────────────────────────────────────────

    def cleanup(self):
        if self.preview_active:
            self.stop_preview()
        elif self.camera is not None:
            try:
                self.camera.close()
                print("[CAMERA] Closed")
            except Exception as e:
                print(f"[CAMERA] Close error: {e}")
        self.camera       = None
        self._initialized = False
        print("[CAMERA] Cleanup complete")