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
        self.controller        = None
        self._retry_timer      = None
        self._retry_countdown  = 0
        self._action_btn_mode  = 'scan'   # 'scan' | 'cancel' | 'retry'
        self.build_ui()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def build_ui(self):
        root = BoxLayout(orientation='vertical', padding=10, spacing=6)

        self.title_label = Label(
            text='MiniK',
            font_size='18sp',
            bold=True,
            size_hint=(1, 0.08)
        )

        self.status_label = Label(
            text='Open MiniK app on your phone\nthen scan this QR code to pair',
            font_size='11sp',
            size_hint=(1, 0.12),
            halign='center',
            valign='middle',
            color=(0.8, 0.8, 0.8, 1)
        )
        self.status_label.bind(
            size=self.status_label.setter('text_size')
        )

        self.qr_image = Image(
            size_hint=(1, 0.75),
            allow_stretch=True,
            keep_ratio=True,
            opacity=1
        )

        self.device_id_label = Label(
            text='',
            font_size='9sp',
            size_hint=(1, 0.06),
            color=(0.5, 0.5, 0.5, 1)
        )

        # Main action button — changes role based on state
        self.action_btn = Button(
            text='Look for\nmy Phone',
            background_color=(0.15, 0.55, 0.15, 1),
            font_size='10sp',
            size_hint=(1, 0.20),
            halign='center'
        )
        self.action_btn.bind(on_press=self._on_action_btn)

        # Bottom row
        btn_row = BoxLayout(
            orientation='horizontal',
            spacing=5
        )

        self.pair_btn = Button(
            text='Connect New\nPhone',
            background_color=(0.15, 0.45, 0.75, 1),
            font_size='10sp',
            halign='center'
        )
        self.pair_btn.bind(
            on_press=lambda x: self.controller.start_pairing()
            if self.controller else None
        )

        self.shutdown_btn = Button(
            text='Power Off',
            background_color=(0.55, 0.1, 0.1, 1),
            font_size='10sp'
        )
        self.shutdown_btn.bind(
            on_press=lambda x: self.controller.shutdown_device()
            if self.controller else None
        )

        btn_row.add_widget(self.pair_btn)
        btn_row.add_widget(self.shutdown_btn)

        root.add_widget(self.title_label)
        root.add_widget(self.status_label)
        root.add_widget(self.qr_image)
        root.add_widget(self.device_id_label)
        root.add_widget(self.action_btn)
        root.add_widget(btn_row)

        if config.SHOW_RESET_BUTTON:
            self.reset_btn = Button(
                text='Reset All Pairings',
                background_color=(0.3, 0.1, 0.1, 1),
                font_size='9sp',
                size_hint=(1, 0.20)
            )
            self.reset_btn.bind(
                on_press=lambda x: self.controller.reset_pairing()
                if self.controller else None
            )
            root.add_widget(self.reset_btn)

        self.add_widget(root)

    # ── Kivy Lifecycle ────────────────────────────────────────────────────────

    def on_enter(self):
        if self.controller:
            self._generate_qr(self.controller.dm.get_device_id())

    # ── State Methods (called by app_controller.py) ───────────────────────────

    def show_scanning(self):
        """BLE scan running"""
        self._stop_all_timers()
        self.status_label.text           = 'Scanning for your phone...'
        self.status_label.color          = (0.5, 0.8, 1.0, 1)
        self.qr_image.opacity            = 0
        self.pair_btn.disabled           = True
        self._action_btn_mode            = 'cancel'
        self.action_btn.text             = 'Cancel'
        self.action_btn.background_color = (0.5, 0.15, 0.15, 1)
        self.action_btn.disabled         = False

    def show_connecting(self, device_name: str):
        """BLE found phone — attempting WiFi hotspot connect"""
        self._stop_all_timers()
        self.status_label.text           = (f'Found {device_name}\n'
                                             f'Connecting to hotspot...')
        self.status_label.color          = (0.3, 0.9, 0.3, 1)
        self.qr_image.opacity            = 0
        self.pair_btn.disabled           = True
        self.action_btn.text             = 'Connecting...'
        self.action_btn.background_color = (0.3, 0.3, 0.3, 1)
        self.action_btn.disabled         = True

    def show_hotspot_prompt(self,
                            device_name: str,
                            attempt: int,
                            retries_left: int,
                            retry_in: int):
        """WiFi failed — phone hotspot is off. Show countdown + retry."""
        self._stop_all_timers()
        self._retry_countdown            = retry_in
        self._hotspot_device             = device_name
        self._hotspot_retries_left       = retries_left

        self.status_label.color          = (1.0, 0.65, 0.15, 1)
        self.qr_image.opacity            = 0
        self.pair_btn.disabled           = False
        self._action_btn_mode            = 'retry'
        self.action_btn.background_color = (0.55, 0.35, 0.05, 1)
        self.action_btn.disabled         = False

        self._update_hotspot_label()

        self._retry_timer = Clock.schedule_interval(
            self._tick_hotspot_prompt, 1.0
        )

    def show_waiting_ble(self):
        """BLE advertising — waiting for phone to scan QR and connect"""
        self._stop_all_timers()
        self.status_label.text           = ('Waiting for phone to connect...\n'
                                             'Scan QR code with MiniK app')
        self.status_label.color          = (0.5, 0.8, 1.0, 1)
        self.qr_image.opacity            = 1
        self.pair_btn.disabled           = True
        self._action_btn_mode            = 'cancel'
        self.action_btn.text             = 'Cancel'
        self.action_btn.background_color = (0.5, 0.15, 0.15, 1)
        self.action_btn.disabled         = False

        if self.controller:
            self._generate_qr(self.controller.dm.get_device_id())

    def show_qr(self, message: str = None):
        """Idle state — QR visible, both buttons active"""
        self._stop_all_timers()
        self.status_label.text           = message or (
            'Open MiniK app on your phone\n'
            'then scan this QR code to pair'
        )
        self.status_label.color          = (0.85, 0.85, 0.85, 1)
        self.qr_image.opacity            = 1
        self.pair_btn.text               = 'Connect New\nPhone'
        self.pair_btn.disabled           = False
        self._action_btn_mode            = 'scan'
        self.action_btn.text             = 'Look for\nmy Phone'
        self.action_btn.background_color = (0.15, 0.55, 0.15, 1)
        self.action_btn.disabled         = False

        if self.controller:
            self._generate_qr(self.controller.dm.get_device_id())

    def show_error(self, message: str):
        self._stop_all_timers()
        self.status_label.text  = message
        self.status_label.color = (1.0, 0.3, 0.3, 1)
        self.pair_btn.disabled  = False
        self.action_btn.disabled = False

    # ── Action Button Dispatcher ──────────────────────────────────────────────

    def _on_action_btn(self, *args):
        if not self.controller:
            return
        if self._action_btn_mode == 'scan':
            self.controller.rescan_for_devices()
        elif self._action_btn_mode == 'cancel':
            self.controller.stop_ble_pairing()
        elif self._action_btn_mode == 'retry':
            self._stop_all_timers()
            self.controller.retry_wifi_now()

    # ── Hotspot Countdown ─────────────────────────────────────────────────────

    def _tick_hotspot_prompt(self, dt):
        self._retry_countdown -= 1
        if self._retry_countdown <= 0:
            self._stop_all_timers()
            return
        self._update_hotspot_label()

    def _update_hotspot_label(self):
        s = self._retry_countdown
        r = self._hotspot_retries_left
        self.status_label.text = (
            f'Enable hotspot on {self._hotspot_device}\n'
            f'Retrying in {s}s  '
            f'({r} attempt{"s" if r != 1 else ""} left)'
        )
        self.action_btn.text = 'Retry Now'

    # ── QR Generation ─────────────────────────────────────────────────────────

    def _generate_qr(self, device_id: str):
        ble_name = f"MiniK-{device_id[-6:]}"
        qr_data  = (
            f"minik://pair"
            f"?device={device_id}"
            f"&ble={ble_name}"
            f"&uuid={GATT_SERVICE_UUID}"
        )
        print(f"[PAIRING] QR generated for {ble_name}")

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

        self.qr_image.texture     = CoreImage(buf, ext='png').texture
        self.device_id_label.text = f"Device: {device_id}"

    # ── Timer Cleanup ─────────────────────────────────────────────────────────

    def _stop_all_timers(self):
        if self._retry_timer:
            self._retry_timer.cancel()
            self._retry_timer = None
