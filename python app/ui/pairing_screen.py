from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.graphics import Color, Rectangle
import qrcode
import io
from kivy.core.image import Image as CoreImage
import config


class PairingScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.controller = None
        self.build_ui()
        
    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        
        # Title
        title = Label(
            text='MiniK\nVOC Detection System',
            font_size='18sp',
            size_hint=(1, 0.3),
            halign='center'
        )
        title.bind(size=title.setter('text_size'))
        
        # QR Code container (initially hidden)
        self.qr_container = BoxLayout(
            orientation='vertical',
            size_hint=(1, 0.5),
            opacity=0
        )
        
        self.qr_image = Image(size_hint=(1, 0.8))
        self.device_id_label = Label(
            text='',
            font_size='12sp',
            size_hint=(1, 0.2)
        )
        
        self.qr_container.add_widget(self.qr_image)
        self.qr_container.add_widget(self.device_id_label)
        
        # Buttons container
        self.button_container = BoxLayout(
            orientation='vertical',
            size_hint=(1, 0.3),
            spacing=10
        )
        
        self.pair_btn = Button(
            text='Pair Device',
            size_hint=(1, 0.5),
            background_color=(0.2, 0.6, 0.8, 1)
        )
        self.pair_btn.bind(on_press=self.on_pair_pressed)
        
        self.shutdown_btn = Button(
            text='Turn Off',
            size_hint=(1, 0.5),
            background_color=(0.8, 0.2, 0.2, 1)
        )
        self.shutdown_btn.bind(on_press=self.on_shutdown)
        
        self.button_container.add_widget(self.pair_btn)
        self.button_container.add_widget(self.shutdown_btn)
        
        # Status label
        self.status_label = Label(
            text='Press "Pair Device" to start',
            font_size='12sp',
            size_hint=(1, 0.1),
            color=(0.7, 0.7, 0.7, 1)
        )
        
        layout.add_widget(title)
        layout.add_widget(self.qr_container)
        layout.add_widget(self.button_container)
        layout.add_widget(self.status_label)
        
        if config.SHOW_RESET_BUTTON:
            self.reset_btn = Button(
                text='Reset Pairing',
                size_hint=(1, 0.15),
                font_size='10sp',
                background_color=(0.5, 0.3, 0.3, 1)
            )
            self.reset_btn.bind(on_press=self.on_reset_pairing)
            layout.add_widget(self.reset_btn)
        
        self.add_widget(layout)
    
    def on_pair_pressed(self, instance):
        if self.controller:
            self.controller.start_pairing()
    
    def show_qr_code(self):
        """Generate and display QR code with device ID"""
        device_id = self.controller.dm.get_device_id()
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(device_id)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to Kivy image
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        core_image = CoreImage(buffer, ext='png')
        self.qr_image.texture = core_image.texture
        
        # Update labels
        self.device_id_label.text = f'Device ID: {device_id}'
        self.status_label.text = 'Waiting for connection...'
        
        # Show QR container
        self.qr_container.opacity = 1
        self.pair_btn.disabled = True
    

    def on_reset_pairing(self, instance):
       if self.controller:
           self.controller.reset_pairing()
    
    def hide_qr_code(self):
        """Hide QR code after timeout"""
        self.qr_container.opacity = 0
        self.pair_btn.disabled = False
        self.status_label.text = 'Pairing timeout. Try again.'
    
    def show_error(self, message):
        self.status_label.text = message
        self.status_label.color = (1, 0.3, 0.3, 1)
    
    def on_shutdown(self, instance):
        if self.controller:
            self.controller.shutdown_device()
