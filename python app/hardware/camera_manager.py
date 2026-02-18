import os
import time
from datetime import datetime
from io import BytesIO
import threading

try:
    from picamera2 import Picamera2
    from libcamera import controls
    HAS_CAMERA = True
except ImportError:
    HAS_CAMERA = False
    print("[CAMERA] picamera2 not available")

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("[CAMERA] PIL not available")

from kivy.graphics.texture import Texture
from kivy.clock import Clock


class CameraManager:
    """Manages Raspberry Pi Camera Module (Rev 1.3, CSI)"""
    
    # Preview resolution (fits 240x320 display)
    PREVIEW_WIDTH = 240
    PREVIEW_HEIGHT = 180
    
    # Capture resolution (full camera res for Rev 1.3)
    CAPTURE_WIDTH = 1640
    CAPTURE_HEIGHT = 1232
    
    def __init__(self):
        self.camera = None
        self.preview_active = False
        self.current_texture = None
        self._lock = threading.Lock()
        self._initialized = False
        
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
            print("[CAMERA] Cannot start preview - not initialized")
            return
        
        if self.preview_active:
            return
        
        try:
            # Configure for preview
            preview_config = self.camera.create_preview_configuration(
                main={
                    "size": (self.PREVIEW_WIDTH, self.PREVIEW_HEIGHT),
                    "format": "RGB888"
                },
                buffer_count=2  # Double buffering for smoother preview
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
                # Capture frame as numpy array
                frame = self.camera.capture_array("main")
                
                # frame is (height, width, 3) in RGB888
                h, w, channels = frame.shape

                # Fix: Convert BGR to RGB
                frame_rgb = frame[:, :, ::-1].copy()
                
                # Create Kivy texture
                texture = Texture.create(size=(w, h), colorfmt='rgb')
                
                # Flip vertically (Kivy uses bottom-left origin)
                flipped = frame[::-1, :, :]
                
                # Blit data to texture
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
            return self.current_texture  # Return last good frame
    
    def capture_image(self):
        """Capture full resolution still image"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"/home/miniK/mini_project/python app/captures/capture_{timestamp}.jpg"
        
        if not HAS_CAMERA or not self._initialized:
            print("[CAMERA] Cannot capture - not initialized")
            return None
        
        try:
            # Stop preview
            was_previewing = self.preview_active
            if was_previewing:
                self.stop_preview()
            
            # Configure for still capture
            still_config = self.camera.create_still_configuration(
                main={
                    "size": (self.CAPTURE_WIDTH, self.CAPTURE_HEIGHT),
                    "format": "RGB888"
                }
            )
            
            self.camera.configure(still_config)
            self.camera.start()
            
            # Allow auto-exposure to settle
            time.sleep(2)
            
            # Capture to file directly
            self.camera.capture_file(filename)
            
            self.camera.stop()
            
            # Restart preview if it was running
            if was_previewing:
                self.start_preview()
            
            print(f"[CAMERA] Image captured: {filename}")
            return filename
            
        except Exception as e:
            print(f"[CAMERA] Error capturing image: {e}")
            # Try to restart preview if it was running
            try:
                if was_previewing:
                    self.start_preview()
            except:
                pass
            return None
    
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
