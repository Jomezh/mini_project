import os
import time
from datetime import datetime
from io import BytesIO

try:
    from picamera2 import Picamera2
    from PIL import Image
    HAS_CAMERA = True
except ImportError:
    HAS_CAMERA = False
    print("Warning: Camera libraries not available. Running in simulation mode.")

from kivy.core.image import Image as CoreImage
from kivy.graphics.texture import Texture


class CameraManager:
    """Manages Raspberry Pi Camera Module"""
    
    def __init__(self):
        self.camera = None
        self.preview_active = False
        self.preview_config = None
        
    def initialize(self):
        """Initialize camera"""
        if not HAS_CAMERA:
            print("Camera running in simulation mode")
            return
        
        try:
            self.camera = Picamera2()
            
            # Configure for preview (lower resolution for performance)
            self.preview_config = self.camera.create_preview_configuration(
                main={"size": (640, 480), "format": "RGB888"}
            )
            
            # Configure for capture (higher resolution)
            self.capture_config = self.camera.create_still_configuration(
                main={"size": (1640, 1232), "format": "RGB888"}
            )
            
            print("Camera initialized successfully")
            
        except Exception as e:
            print(f"Error initializing camera: {e}")
            self.camera = None
    
    def start_preview(self):
        """Start camera preview"""
        if not HAS_CAMERA or self.camera is None:
            return
        
        try:
            if not self.preview_active:
                self.camera.configure(self.preview_config)
                self.camera.start()
                self.preview_active = True
                print("Camera preview started")
        except Exception as e:
            print(f"Error starting preview: {e}")
    
    def stop_preview(self):
        """Stop camera preview"""
        if not HAS_CAMERA or self.camera is None:
            return
        
        try:
            if self.preview_active:
                self.camera.stop()
                self.preview_active = False
                print("Camera preview stopped")
        except Exception as e:
            print(f"Error stopping preview: {e}")
    
    def get_preview_texture(self):
        """Get current preview frame as Kivy texture"""
        if not HAS_CAMERA or self.camera is None or not self.preview_active:
            return None
        
        try:
            # Capture frame from preview
            frame = self.camera.capture_array()
            
            # Convert to PIL Image
            pil_image = Image.fromarray(frame)
            
            # Resize to fit display (240x320)
            pil_image = pil_image.resize((240, 180))
            
            # Convert to Kivy texture
            buf = BytesIO()
            pil_image.save(buf, format='PNG')
            buf.seek(0)
            
            core_image = CoreImage(buf, ext='png')
            return core_image.texture
            
        except Exception as e:
            print(f"Error getting preview texture: {e}")
            return None
    
    def capture_image(self):
        """Capture high-resolution image"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"/tmp/capture_{timestamp}.jpg"
        
        if not HAS_CAMERA or self.camera is None:
            # Simulation mode - create dummy image
            return self._create_dummy_image(filename)
        
        try:
            # Stop preview if active
            was_previewing = self.preview_active
            if was_previewing:
                self.stop_preview()
            
            # Configure for still capture
            self.camera.configure(self.capture_config)
            self.camera.start()
            
            # Allow camera to adjust
            time.sleep(1)
            
            # Capture image
            self.camera.capture_file(filename)
            
            # Stop capture
            self.camera.stop()
            
            # Restart preview if it was active
            if was_previewing:
                self.start_preview()
            
            print(f"Image captured: {filename}")
            return filename
            
        except Exception as e:
            print(f"Error capturing image: {e}")
            return None
    
    def _create_dummy_image(self, filename):
        """Create a dummy image for simulation"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a simple image
            img = Image.new('RGB', (1640, 1232), color='lightgray')
            draw = ImageDraw.Draw(img)
            
            # Add text
            text = "SIMULATION MODE\nFood Sample"
            draw.text((820, 616), text, fill='black', anchor='mm')
            
            # Save
            img.save(filename)
            return filename
            
        except Exception as e:
            print(f"Error creating dummy image: {e}")
            return None
    
    def cleanup(self):
        """Cleanup camera resources"""
        if self.preview_active:
            self.stop_preview()
        
        if HAS_CAMERA and self.camera is not None:
            try:
                self.camera.close()
            except:
                pass
        
        print("Camera manager cleaned up")
