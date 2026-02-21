import qrcode
import config
from io import BytesIO
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock


# Must match ble_manager.py exactly
GATT_SERVICE_UUID = '12345678-1234-1234-1234-123456789ab0'


class PairingScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.controller = None
        self.build_ui()

    def build_ui(self):
        layout = BoxLayout(
            orientation='vertical',
            padding=10,
            spacing=8
        )

        # Title
        self.title_label = Label(
            text='MiniK Setup',
            font_size='16sp',
            bold=True,
            size_hint=(1, 0.1)
        )

        # Status label
        self.status_label = Label(
            text='Scan QR code to pair',
            font_size='11sp',
            size_hint=(1, 0.1),
            color=(0.7, 0.7, 0.7, 1)
        )

        # QR code image
        self.qr_image = Image(
            size_hint=(1, 0.55),
            allow_stretch=True,
            keep_ratio=True
        )

        # Device ID label (shown below QR)
        self.device_id_label = Label(
            text='',
            font_size='9sp',
            size_hint=(1, 0.08),
            color=(0.5, 0.5, 0.5, 1)
        )

        # Buttons
        btn_box = BoxLayout(
            orientation='horizontal',
            size_hint=(1, 0.12),
            spacing=5
        )

        self.pair_btn = Button(
            text='Start Pairing',
            background_color=(0.2, 0.6, 0.8, 1),
            font_size='11sp'
        )
        self.pair_btn.bind(on_press=lambda x: self.controller.start_pairing()
                           if self.controller else None)

        self.shutdown_btn = Button(
            text='Power Off',
            background_color=(0.8, 0.2, 0.2, 1),
            font_size='11sp'
        )
        self.shutdown_btn.bind(on_press=lambda x: self.controller.shutdown_device()
                               if self.controller else None)

        btn_box.add_widget(self.pair_btn)
        btn_box.add_widget(self.shutdown_btn)

        # Reset button (dev only)
        if config.SHOW_RESET_BUTTON:
            self.reset_btn = Button(
                text='Reset Pairing',
                background_color=(0.4, 0.2, 0.2, 1),
                font_size='9sp',
                size_hint=(1, 0.08)
            )
            self.reset_btn.bind(on_press=lambda x: self.controller.reset_pairing()
                                if self.controller else None)

        layout.add_widget(self.title_label)
        layout.add_widget(self.status_label)
        layout.add_widget(self.qr_image)
        layout.add_widget(self.device_id_label)
        layout.add_widget(btn_box)

        if config.SHOW_RESET_BUTTON:
            layout.add_widget(self.reset_btn)

        self.add_widget(layout)

    def on_enter(self):
        """Generate QR code as soon as screen is shown"""
        if self.controller:
            device_id = self.controller.dm.get_device_id()
            self._generate_qr(device_id)

    def _generate_qr(self, device_id):
        """
        Generate QR code with deep link containing:
        - device ID      → for display/verification
        - BLE short name → phone uses to filter BLE scan
        - Service UUID   → phone connects directly to correct GATT service
        """
        # BLE advertised name (last 6 chars of device ID)
        ble_name = f"MiniK-{device_id[-6:]}"

        # Deep link that phone app intercepts
        # Format: minik://pair?device=X&ble=Y&uuid=Z
        qr_data = (
            f"minik://pair"
            f"?device={device_id}"
            f"&ble={ble_name}"
            f"&uuid={GATT_SERVICE_UUID}"
        )

        print(f"[PAIRING] QR data: {qr_data}")

        # Generate QR code image
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=4,
            border=2
        )
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color='white', back_color='black')

        # Convert to Kivy texture
        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)

        core_img = CoreImage(buf, ext='png')
        self.qr_image.texture = core_img.texture

        # Show device ID below QR
        self.device_id_label.text = f"Device: {device_id}"

        print(f"[PAIRING] QR code generated for {ble_name}")

    def show_qr_code(self):
        self.status_label.text = 'Scan with MiniK app to connect'
        self.status_label.color = (0.4, 0.8, 0.4, 1)
        self.pair_btn.disabled = True

    def hide_qr_code(self):
        self.status_label.text = 'Pairing timed out - try again'
        self.status_label.color = (1, 0.5, 0.3, 1)
        self.pair_btn.disabled = False

    def show_checking_connection(self):
        self.status_label.text = 'Checking connection...'
        self.status_label.color = (0.7, 0.7, 0.7, 1)
        self.pair_btn.disabled = True

    def show_error(self, message):
        self.status_label.text = message
        self.status_label.color = (1, 0.3, 0.3, 1)
        self.pair_btn.disabled = False

    def reset_ui(self):
        self.status_label.text = 'Scan QR code to pair'
        self.status_label.color = (0.7, 0.7, 0.7, 1)
        self.pair_btn.disabled = False
        # Regenerate QR with fresh state
        if self.controller:
            device_id = self.controller.dm.get_device_id()
            self._generate_qr(device_id)
