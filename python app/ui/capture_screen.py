from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.clock import Clock


class CaptureScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.controller = None
        self.preview_event = None
        self.build_ui()
        
    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Title
        title = Label(
            text='Capture Food Image',
            font_size='14sp',
            size_hint=(1, 0.1),
            bold=True
        )
        
        # Camera preview
        self.preview = Image(
            size_hint=(1, 0.7),
            allow_stretch=True,
            keep_ratio=True
        )
        
        # Buttons
        button_box = BoxLayout(
            orientation='horizontal',
            size_hint=(1, 0.15),
            spacing=10
        )
        
        self.capture_btn = Button(
            text='Capture',
            background_color=(0.2, 0.6, 0.8, 1),
            font_size='13sp'
        )
        self.capture_btn.bind(on_press=self.on_capture)
        
        back_btn = Button(
            text='Back',
            background_color=(0.5, 0.5, 0.5, 1),
            font_size='13sp'
        )
        back_btn.bind(on_press=self.on_back)
        
        button_box.add_widget(self.capture_btn)
        button_box.add_widget(back_btn)
        
        # Status
        self.status_label = Label(
            text='Position food item in frame',
            font_size='10sp',
            size_hint=(1, 0.05),
            color=(0.7, 0.7, 0.7, 1)
        )
        
        layout.add_widget(title)
        layout.add_widget(self.preview)
        layout.add_widget(button_box)
        layout.add_widget(self.status_label)
        
        self.add_widget(layout)
    
    def on_enter(self):
        """Auto start preview when entering screen"""
        self.start_preview()
    
    def start_preview(self):
        """Start camera preview"""
        if self.controller:
            self.controller.dm.hardware.start_camera_preview()
            
            # Pi Zero 2W is limited - 10fps is enough for preview
            # Avoid going faster, it will lag
            self.preview_event = Clock.schedule_interval(
                self.update_preview,
                1.0 / 10  # 10 FPS
            )
    
    def update_preview(self, dt):
        """Update preview image from camera texture"""
        if self.controller:
            texture = self.controller.dm.hardware.get_preview_texture()
            if texture:
                self.preview.texture = texture
    
    def stop_preview(self):
        """Stop camera preview"""
        if self.preview_event:
            self.preview_event.cancel()
            self.preview_event = None
        
        if self.controller:
            self.controller.dm.hardware.stop_camera_preview()
    
    def on_capture(self, instance):
        if self.controller:
            self.stop_preview()
            self.status_label.text = 'Capturing...'
            self.controller.capture_image()
    
    def on_back(self, instance):
        self.stop_preview()
        self.manager.current = 'home'
    
    def disable_capture(self):
        self.capture_btn.disabled = True
        self.status_label.text = 'Sending to phone...'
    
    def enable_capture(self):
        self.capture_btn.disabled = False
        self.status_label.text = 'Position food item in frame'
    
    def show_error(self, message):
        self.status_label.text = message
        self.status_label.color = (1, 0.3, 0.3, 1)
        self.enable_capture()
    
    def on_leave(self):
        """Auto stop preview when leaving screen"""
        self.stop_preview()
