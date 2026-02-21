import qrcode
import config
from io import BytesIO
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage

GATT_SERVICE_UUID  = '12345678-1234-1234-1234-123456789ab0'
WIFI_RETRY_LIMIT   = 3   # Keep in sync with app_controller.py


class PairingScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.controller = None
        self._build_ui()

    def _build_ui(self):
        layout = BoxLayout(
            orientation='vertical',
            padding=10, spacing=6
        )

        # Title
        self.title_label = Label(
            text='MiniK',
            font_size='16sp', bold=True,
            size_hint=(1, 0.08)
        )

        # Status - multi-line friendly
        self.status_label = Label(
            text='Starting...',
            font_size='10sp',
            size_hint=(1, 0.18),
            color=(0.8, 0.8, 0.8, 1),
            halign='center',
            valign='middle',
            text_size=(220, None)
        )

        # QR code image
        self.qr_image = Image(
            size_hint=(1, 0.45),
            allow_stretch=True,
            keep_ratio=True,
            opacity=0
        )

        # Device ID below QR
        self.device_id_label = Label(
            text='',
            font_size='8sp',
            size_hint=(1, 0.05),
            color=(0.4, 0.4, 0.4, 1)
        )

        # Button row
        btn_box = BoxLayout(
            orientation='horizontal',
            size_hint=(1, 0.11), spacing=4
        )

        self.pair_btn = Button(
            text='Pair New Device',
            background_color=(0.2, 0.6, 0.8, 1),
            font_size='10sp',
            opacity=0, disabled=True
        )
        self.pair_btn.bind(
            on_press=lambda x: self.controller.start_pairing()
            if self.controller else None
        )

        self.action_btn = Button(
            text='Scan Again',
            background_color=(0.3, 0.6, 0.3, 1),
            font_size='10sp',
            opacity=0, disabled=True
        )
        # action_btn is reused for both Scan Again and Retry Now

        self.shutdown_btn = Button(
            text='Power Off',
            background_color=(0.7, 0.2, 0.2, 1),
            font_size='10sp'
        )
        self.shutdown_btn.bind(
            on_press=lambda x: self.controller.shutdown_device()
            if self.controller else None
        )

        btn_box.add_widget(self.pair_btn)
        btn_box.add_widget(self.action_btn)
        btn_box.add_widget(self.shutdown_btn)

        layout.add_widget(self.title_label)
        layout.add_widget(self.status_label)
        layout.add_widget(self.qr_image)
        layout.add_widget(self.device_id_label)
        layout.add_widget(btn_box)

        if config.SHOW_RESET_BUTTON:
            reset_btn = Button(
                text='Reset All Pairings',
                background_color=(0.4, 0.2, 0.2, 1),
                font_size='9sp',
                size_hint=(1, 0.08)
            )
            reset_btn.bind(
                on_press=lambda x: self.controller.reset_pairing()
                if self.controller else None
            )
            layout.add_widget(reset_btn)

        self.add_widget(layout)

    # ── Screen States ──────────────────────────────────

    def show_scanning(self):
        """Boot: scanning BLE for known devices"""
        self.status_label.text  = 'Looking for your device...'
        self.status_label.color = (0.7, 0.7, 0.7, 1)
        self.qr_image.opacity   = 0
        self._hide_pair_btn()
        self._hide_action_btn()

    def show_connecting(self, device_name):
        """BLE found - now trying WiFi/hotspot"""
        self.status_label.text  = f'Found {device_name}\nConnecting to hotspot...'
        self.status_label.color = (0.4, 0.8, 0.4, 1)
        self.qr_image.opacity   = 0
        self._hide_pair_btn()
        self._hide_action_btn()

    def show_hotspot_prompt(self, device_name, attempt, retries_left, retry_in):
        """
        BLE found but hotspot is OFF.
        Phone has been notified via BLE to enable hotspot.
        """
        self.status_label.text = (
            f'{device_name} is nearby\n'
            f'but hotspot is OFF.\n'
            f'Enable hotspot on your phone.\n'
            f'Retrying in {retry_in}s '
            f'({retries_left} attempt{"s" if retries_left != 1 else ""} left)'
        )
        self.status_label.color = (1.0, 0.65, 0.1, 1)   # Orange = warning
        self.qr_image.opacity   = 0
        self._hide_pair_btn()

        # Retry Now button
        self.action_btn.text     = 'Retry Now'
        self.action_btn.opacity  = 1
        self.action_btn.disabled = False
        self.action_btn.unbind(on_press=self._action_btn_callback
                               if hasattr(self, '_action_btn_callback') else lambda *a: None)
        self._action_btn_callback = lambda x: self.controller.retry_wifi_now() \
            if self.controller else None
        self.action_btn.bind(on_press=self._action_btn_callback)

    def show_waiting_ble(self):
        """BLE advertising, waiting for phone to scan QR"""
        self.status_label.text  = 'Waiting for phone app\nto connect...'
        self.status_label.color = (0.4, 0.7, 1.0, 1)
        self._hide_pair_btn()
        self._hide_action_btn()

    def show_qr(self, message=None):
        """No known device nearby - show QR for new/re-pairing"""
        self.status_label.text  = message or 'Scan QR code with\nMiniK app to pair'
        self.status_label.color = (0.9, 0.9, 0.9, 1)

        if self.controller:
            self._generate_qr(self.controller.dm.get_device_id())

        self.qr_image.opacity = 1

        # Pair New Device button
        self.pair_btn.opacity  = 1
        self.pair_btn.disabled = False

        # Scan Again button
        self.action_btn.text     = 'Scan Again'
        self.action_btn.opacity  = 1
        self.action_btn.disabled = False
        self.action_btn.unbind(on_press=self._action_btn_callback
                               if hasattr(self, '_action_btn_callback') else lambda *a: None)
        self._action_btn_callback = lambda x: self.controller.rescan_for_devices() \
            if self.controller else None
        self.action_btn.bind(on_press=self._action_btn_callback)

    def show_error(self, message):
        self.status_label.text  = message
        self.status_label.color = (1, 0.3, 0.3, 1)
        self.pair_btn.opacity   = 1
        self.pair_btn.disabled  = False

    def reset_ui(self):
        self.show_qr()

    # ── Helpers ────────────────────────────────────────

    def _hide_pair_btn(self):
        self.pair_btn.opacity  = 0
        self.pair_btn.disabled = True

    def _hide_action_btn(self):
        self.action_btn.opacity  = 0
        self.action_btn.disabled = True

    def _generate_qr(self, device_id):
        ble_name = f"MiniK-{device_id[-6:]}"
        qr_data  = (
            f"minik://pair"
            f"?device={device_id}"
            f"&ble={ble_name}"
            f"&uuid={GATT_SERVICE_UUID}"
        )
        print(f"[PAIRING] QR: {qr_data}")

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=4,
            border=2
        )
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color='white', back_color='black')
        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)

        core_img = CoreImage(buf, ext='png')
        self.qr_image.texture      = core_img.texture
        self.device_id_label.text  = f"Device: {device_id}"
