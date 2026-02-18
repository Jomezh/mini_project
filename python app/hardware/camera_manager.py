import os
import time
from datetime import datetime
from io import BytesIO
import threading

try:
    from picamera2 import Picamera2
    HAS_CAMERA = True
except ImportError:
    HAS_CAMERA = False
    print("[CAMERA] picamera2 not available")

from kivy.graphics.texture import Texture


class CameraManager:
    """Manages Raspberry Pi Camera Module (Rev 1.3, CSI)"""
    
    PREVIEW_WIDTH = 240
    PREVIEW_HEIGHT = 180
    CAPTURE_WIDTH = 1640
    CAPTURE_HEIGHT = 1232
    
    def __init__(self):
        self.camera = None
        self.preview_active = False
        self.current_texture = None
        self._lock = threading.Lock()
        self._initialized = False
        self._capturing = False
        
    def initialize(self):
        """Initialize camera"""
        if not HAS_CAMERA:
            print("[CAMERA] Running in simulation mode")
            return
        
        try:
            self.camera = Picamera2()
            self._initialized = True
            print("[CAMERA] Picamera2 initialized successfully")
        except Exception as e:
            print(f"[CAMERA] Initialization failed: {e}")
            self.camera = None
            self._initialized = False
    
    def start_preview(self):
        """Start camera preview"""
        if not HAS_CAMERA or not self._initialized or self.camera is None:
            return
        
        if self.preview_active:
            return
        
        try:
            preview_config = self.camera.create_preview_configuration(
                main={
                    "size": (self.PREVIEW_WIDTH, self.PREVIEW_HEIGHT),
                    "format": "RGB888"
                },
                buffer_count=2
            )
            self.camera.configure(preview_config)
            self.camera.start()
            self.preview_active = True
            print("[CAMERA] Preview started")
        except Exception as e:
            print(f"[CAMERA] Error starting preview: {e}")
            self.preview_active = False
    
    def stop_preview(self):
        """Stop camera preview"""
        if not HAS_CAMERA or self.camera is None:
            return
        
        try:
            if self.preview_active:
                self.camera.stop()
                self.preview_active = False
                self.current_texture = None
                print("[CAMERA] Preview stopped")
        except Exception as e:
            print(f"[CAMERA] Error stopping preview: {e}")
    
    def get_preview_texture(self):
        """Get current preview frame as Kivy texture"""
        if not HAS_CAMERA or not self.preview_active or self.camera is None:
            return None
        
        try:
            with self._lock:
                frame = self.camera.capture_array("main")
                h, w, _ = frame.shape
                
                # Fix blue tint: flip BGR to RGB
                frame_rgb = frame[:, :, ::-1].copy()
                
                # Flip vertically for Kivy
                flipped = frame_rgb[::-1, :, :]
                
                texture = Texture.create(size=(w, h), colorfmt='rgb')
                texture.blit_buffer(
                    flipped.tobytes(),
                    colorfmt='rgb',
                    bufferfmt='ubyte'
                )
                
                self.current_texture = texture
                return texture
                
        except Exception as e:
            print(f"[CAMERA] Error getting preview frame: {e}")
            return self.current_texture
    
    def capture_image(self):
        """Capture full resolution still image"""
        if self._capturing:
            print("[CAMERA] Capture already in progress")
            return None
        
        self._capturing = True
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        captures_dir = os.path.join(base_dir, 'captures')
        os.makedirs(captures_dir, exist_ok=True)
        filename = os.path.join(captures_dir, f"capture_{timestamp}.jpg")
        
        was_previewing = self.preview_active
        
        try:
            if was_previewing:
                self.stop_preview()
                time.sleep(0.5)
            
            still_config = self.camera.create_still_configuration(
                main={
                    "size": (self.CAPTURE_WIDTH, self.CAPTURE_HEIGHT),
                    "format": "RGB888"
                }
            )
            
            self.camera.configure(still_config)
            self.camera.start()
            time.sleep(2)
            self.camera.capture_file(filename)
            self.camera.stop()
            
            print(f"[CAMERA] Image captured: {filename}")
            return filename
            
        except Exception as e:
            print(f"[CAMERA] Error capturing image: {e}")
            try:
                self.camera.stop()
            except:
                pass
            return None
            
        finally:
            self._capturing = False
            try:
                if was_previewing:
                    self.start_preview()
            except:
                pass
    
    def cleanup(self):
        """Release camera resources"""
        if self.preview_active:
            self.stop_preview()
        
        if self.camera is not None:
            try:
                self.camera.close()
                print("[CAMERA] Camera closed")
            except Exception as e:
                print(f"[CAMERA] Error closing camera: {e}")
        
        self._initialized = False
