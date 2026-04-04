# hardware/camera_manager.py

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


class CameraTimeoutError(Exception):
    """
    Raised by capture_image() when the camera hangs instead of responding.
    Typically caused by a loose ribbon cable connection.
    Callers should catch this and show a retry prompt.
    """
    pass


class CameraManager:

    PREVIEW_WIDTH  = 240
    PREVIEW_HEIGHT = 180
    CAPTURE_WIDTH  = 2592
    CAPTURE_HEIGHT = 1944

    _RELEASE_DELAY   = 1.2
    _CAPTURE_TIMEOUT = 15   # seconds — raise CameraTimeoutError if exceeded


    def __init__(self):
        self.camera          = None
        self.current_texture = None
        self._lock           = threading.Lock()
        self._state_lock     = threading.Lock()
        self._initialized    = False
        self._last_error     = None
        self._state          = 'idle'
        # States: idle | starting | previewing | capturing | stopping


    # ── Properties ────────────────────────────────────────────────────────────


    @property
    def preview_active(self):
        return self._state == 'previewing'


    @property
    def _starting(self):
        """Exposes the 'starting' state so capture_screen._poll_camera_ready
        can distinguish 'still starting' from 'failed to start'."""
        return self._state == 'starting'


    # ── Lifecycle ─────────────────────────────────────────────────────────────


    def initialize(self):
        if not HAS_CAMERA:
            print("[CAMERA] Simulation mode (picamera2 not found)")
            return
        self._initialized = True
        print("[CAMERA] Initialized")


    def cleanup(self):
        self.stop_preview()
        self._initialized = False
        print("[CAMERA] Cleanup done")


    # ── Internal helpers ───────────────────────────────────────────────────────


    def _hard_close(self, cam):
        if cam is None:
            return
        try:
            cam.stop()
        except Exception:
            pass
        try:
            cam.close()
        except Exception:
            pass


    def _set_state(self, state):
        with self._state_lock:
            old = self._state
            self._state = state
        if old != state:
            print(f"[CAMERA] State: {old} → {state}")


    def _run_with_timeout(self, fn, timeout, cam_holder):
        """
        Runs fn() in a daemon thread with a hard timeout.

        fn()        — camera work to execute
        timeout     — seconds before CameraTimeoutError is raised
        cam_holder  — dict with key 'cam'; fn must write the Picamera2
                      instance here as soon as it is created so the caller
                      can attempt cleanup even after a timeout.

        Returns fn's return value.
        Raises CameraTimeoutError if the thread does not finish in time.
        Re-raises any exception thrown inside fn.
        """
        result = {"value": None, "error": None, "done": False}

        def _worker():
            try:
                result["value"] = fn()
            except Exception as e:
                result["error"] = e
            finally:
                result["done"] = True

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        t.join(timeout=timeout)

        if not result["done"]:
            raise CameraTimeoutError(
                f"Camera stopped responding after {timeout}s — "
                "check the ribbon cable and try again"
            )
        if result["error"]:
            raise result["error"]
        return result["value"]


    # ── Preview ────────────────────────────────────────────────────────────────


    def start_preview(self):
        if not HAS_CAMERA or not self._initialized:
            return

        with self._state_lock:
            if self._state in ('starting', 'previewing'):
                print(f"[CAMERA] start_preview() ignored — state={self._state}")
                return
            if self._state in ('capturing', 'stopping'):
                print(f"[CAMERA] start_preview() deferred — waiting for {self._state}")
                threading.Thread(
                    target=self._deferred_start_preview,
                    daemon=True
                ).start()
                return
            self._state = 'starting'

        self._last_error = None
        threading.Thread(target=self._start_preview_worker, daemon=True).start()


    def _deferred_start_preview(self):
        deadline = time.time() + 10.0
        while time.time() < deadline:
            with self._state_lock:
                if self._state == 'idle':
                    break
            time.sleep(0.2)
        self.start_preview()


    def _start_preview_worker(self):
        cam = None
        try:
            time.sleep(self._RELEASE_DELAY)
            cam = Picamera2()
            cfg = cam.create_preview_configuration(
                main={
                    'size':   (self.PREVIEW_WIDTH, self.PREVIEW_HEIGHT),
                    'format': 'RGB888',
                },
                buffer_count=4
            )
            cam.configure(cfg)
            cam.start()

            with self._state_lock:
                if self._state != 'starting':
                    print(f"[CAMERA] Preview worker aborted — state={self._state}")
                    self._hard_close(cam)
                    return
                self.camera = cam
                self._state = 'previewing'

            print("[CAMERA] Preview started")

        except Exception as e:
            self._last_error = e
            print(f"[CAMERA] Preview start error: {e}")
            self._hard_close(cam)
            with self._state_lock:
                self.camera = None
                self._state = 'idle'


    def stop_preview(self):
        if not HAS_CAMERA:
            return

        with self._state_lock:
            if self._state not in ('previewing', 'starting'):
                return
            cam          = self.camera
            self.camera  = None
            self._state  = 'stopping'

        try:
            self._hard_close(cam)
        finally:
            self.current_texture = None
            with self._state_lock:
                self._state = 'idle'
            print("[CAMERA] Preview stopped")


    def get_preview_texture(self):
        if not HAS_CAMERA or self._state != 'previewing':
            return self.current_texture

        with self._lock:
            cam = self.camera
            if cam is None:
                return self.current_texture
            try:
                frame   = cam.capture_array("main")
                h, w, _ = frame.shape
                flipped = frame[::-1, :, :].copy()
                texture = Texture.create(size=(w, h), colorfmt='bgr')
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
        return self._state == 'previewing'


    def get_last_error(self):
        return self._last_error


    # ── Capture ────────────────────────────────────────────────────────────────


    def capture_image(self):
        """
        Takes a still image and returns the saved file path.

        Returns:
            str  — absolute path to the captured JPEG on success.

        Raises:
            CameraTimeoutError — ribbon cable is loose / camera unresponsive.
                                 Caller should show a retry prompt.
            Exception          — any other camera hardware error.
        """
        with self._state_lock:
            if self._state == 'capturing':
                print("[CAMERA] Capture already in progress")
                return None
            preview_cam  = self.camera
            self.camera  = None
            self._state  = 'capturing'

        if preview_cam is not None:
            print("[CAMERA] Stopping preview for capture...")
            self._hard_close(preview_cam)
            self.current_texture = None
            time.sleep(self._RELEASE_DELAY)

        timestamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        captures_dir = os.path.join(base_dir, 'captures')
        os.makedirs(captures_dir, exist_ok=True)
        filename = os.path.join(captures_dir, f"capture_{timestamp}.jpg")

        # cam_holder lets the finally block close the camera even if
        # _run_with_timeout raises before the daemon thread returns.
        cam_holder = {"cam": None}

        try:
            def _do_capture():
                cam = Picamera2()
                cam_holder["cam"] = cam         # expose early for cleanup
                cfg = cam.create_still_configuration(
                    main={
                        'size':   (self.CAPTURE_WIDTH, self.CAPTURE_HEIGHT),
                        'format': 'RGB888',
                    }
                )
                cam.configure(cfg)
                cam.start()
                time.sleep(2.0)
                cam.capture_file(filename)
                return filename

            path = self._run_with_timeout(
                _do_capture,
                self._CAPTURE_TIMEOUT,
                cam_holder,
            )
            print(f"[CAMERA] Captured: {path}")
            return path

        except CameraTimeoutError:
            err = CameraTimeoutError(
                "Camera stopped responding — check the ribbon cable and try again"
            )
            self._last_error = err
            print("[CAMERA] Capture timed out — ribbon loose?")
            raise err

        except Exception as e:
            self._last_error = e
            print(f"[CAMERA] Capture error: {e}")
            raise

        finally:
            # Best-effort cleanup — daemon thread may still hold the resource
            # after a timeout, but this prevents leaks on normal errors.
            self._hard_close(cam_holder["cam"])
            with self._state_lock:
                self.camera = None
                self._state = 'idle'
            print("[CAMERA] Capture done — state reset to idle")