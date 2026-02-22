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

GATT_SERVICE_UUID = '12345678-1234-1234-1234-123456789ab0'
BLE_ADV_TIMEOUT   = 180   # Keep in sync with app_controller.py
WIFI_RETRY_LIMIT  = 3     # Keep in sync with app_controller.py


class PairingScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.controller       = None
        self._action_btn_mode = 'scan'   # 'scan' or 'retry'
        self._scan_timer      = None
        self._ble_timer       = None
        self._scan_elapsed    = 0
        self._ble_remaining   = BLE_ADV_TIMEOUT
        self._build_ui()

    def _build_ui(self):
        layout = BoxLayout(
            orientation='vertical',
            padding=10, spacing=6
        )

        # Title
        self.title_label = Label(
            text='MiniK',
            font_size='16sp',
            bold=True,
            size_hint=(1, 0.08)
        )

        # Status label - multi-line, centred
        self.status_label = Label(
            text='Starting...',
            font_size='10sp',
            size_hint=(1, 0.18),
            color=(0.8, 0.8, 0.8, 1),
            halign='center',
            valign='middle'
        )
        self.status_label.bind(size=self.status_label.setter('text_size'))

        # QR code image
        self.qr_image = Image(
            size_hint=(1, 0.45),
            allow_stretch=True,
            keep_ratio=True,
            opacity=0
        )

        # Device ID shown below QR
        self.device_id_label = Label(
            text='',
            font_size='8sp',
            size_hint=(1, 0.05),
            color=(0.4, 0.4, 0.4, 1)
        )

        # Button row
        btn_box = BoxLayout(
            orientation='horizontal',
            size_hint=(1, 0.25),
            spacing=4
        )

        # "Connect New Phone" - starts BLE advertising
        self.pair_btn = Button(
            text='Connect New\nPhone',
            background_color=(0.2, 0.6, 0.8, 1),
            font_size='9sp',
            halign='center',
            opacity=0,
            disabled=True
        )
        self.pair_btn.bind(on_press=self._on_pair_btn_press)

        # Dual-mode button: "Look for my Phone" OR "Retry Now"
        # Mode is switched via self._action_btn_mode
        # Single binding - no double-bind bug
        self.action_btn = Button(
            text='Look for\nmy Phone',
            background_color=(0.3, 0.6, 0.3, 1),
            font_size='9sp',
            halign='center',
            opacity=0,
            disabled=True
        )
        self.action_btn.bind(on_press=self._on_action_btn_press)

        self.shutdown_btn = Button(
            text='Power Off',
            background_color=(0.7, 0.2, 0.2, 1),
            font_size='10sp'
        )
        self.shutdown_btn.bind(on_press=self._on_shutdown_press)

        btn_box.add_widget(self.pair_btn)
        btn_box.add_widget(self.action_btn)
        btn_box.add_widget(self.shutdown_btn)

        layout.add_widget(self.title_label)
        layout.add_widget(self.status_label)
        layout.add_widget(self.qr_image)
        layout.add_widget(self.device_id_label)
        layout.add_widget(btn_box)

        # Dev-only reset button
        if config.SHOW_RESET_BUTTON:
            reset_btn = Button(
                text='Reset All Pairings',
                background_color=(0.4, 0.2, 0.2, 1),
                font_size='9sp',
                size_hint=(1, 0.2)
            )
            reset_btn.bind(on_press=self._on_reset_press)
            layout.add_widget(reset_btn)

        self.add_widget(layout)

    # ── Button Handlers ────────────────────────────────

    def _on_pair_btn_press(self, instance):
        if self.controller:
            self.controller.start_pairing()

    def _on_action_btn_press(self, instance):
        """Single handler - behaviour driven by _action_btn_mode"""
        if not self.controller:
            return
        if self._action_btn_mode == 'scan':
            self.controller.rescan_for_devices()
        elif self._action_btn_mode == 'retry':
            self.controller.retry_wifi_now()

    def _on_shutdown_press(self, instance):
        if self.controller:
            self.controller.shutdown_device()

    def _on_reset_press(self, instance):
        if self.controller:
            self.controller.reset_pairing()

    # ── Timer Management ───────────────────────────────

    def _stop_all_timers(self):
        for attr in ('_scan_timer', '_ble_timer'):
            timer = getattr(self, attr, None)
            if timer:
                timer.cancel()
                setattr(self, attr, None)

    def _tick_scan_label(self, dt):
        self._scan_elapsed += 1
        dots = '.' * (self._scan_elapsed % 4)
        self.status_label.text = (
            f'Looking for your phone{dots}\n({self._scan_elapsed}s)'
        )

    def _tick_ble_label(self, dt):
        self._ble_remaining -= 1
        if self._ble_remaining <= 0:
            self._stop_all_timers()
            return
        self.status_label.text = (
            f'Waiting for MiniK app\nto connect... ({self._ble_remaining}s)'
        )

    # ── Screen States ──────────────────────────────────

    def show_scanning(self):
        """Boot state: scanning BLE for known devices with live counter"""
        self._stop_all_timers()
        self._scan_elapsed      = 0
        self.status_label.text  = 'Looking for your phone...\n(0s)'
        self.status_label.color = (0.7, 0.7, 0.7, 1)
        self.qr_image.opacity   = 0
        self.device_id_label.text = ''
        self._hide_pair_btn()
        self._hide_action_btn()
        self._scan_timer = Clock.schedule_interval(self._tick_scan_label, 1)

    def show_connecting(self, device_name):
        """Known BLE device found - attempting WiFi/hotspot"""
        self._stop_all_timers()
        self.status_label.text  = f'Found {device_name}\nConnecting to hotspot...'
        self.status_label.color = (0.4, 0.8, 0.4, 1)
        self.qr_image.opacity   = 0
        self._hide_pair_btn()
        self._hide_action_btn()

    def show_hotspot_prompt(self, device_name, attempt, retries_left, retry_in):
        """
        BLE confirmed phone nearby but hotspot is OFF.
        Phone has been notified via BLE to turn on hotspot.
        """
        self._stop_all_timers()
        self.status_label.text = (
            f'{device_name} is nearby\n'
            f'but hotspot is OFF.\n'
            f'Enable hotspot on your phone.\n'
            f'Retrying in {retry_in}s '
            f'({retries_left} attempt{"s" if retries_left != 1 else ""} left)'
        )
        self.status_label.color  = (1.0, 0.65, 0.1, 1)   # Orange = warning
        self.qr_image.opacity    = 0
        self._hide_pair_btn()

        # Switch action button to Retry Now
        self._action_btn_mode    = 'retry'
        self.action_btn.text     = 'Retry Now'
        self.action_btn.opacity  = 1
        self.action_btn.disabled = False

    def show_waiting_ble(self):
        """
        BLE advertising is running.
        QR stays visible. Countdown shows time left.
        """
        self._stop_all_timers()
        self._ble_remaining     = BLE_ADV_TIMEOUT
        self.status_label.text  = (
            f'Waiting for MiniK app\n'
            f'to connect... ({self._ble_remaining}s)'
        )
        self.status_label.color = (0.4, 0.7, 1.0, 1)

        # Keep QR visible so user can scan with phone
        self.qr_image.opacity   = 1

        self._hide_pair_btn()
        self._hide_action_btn()
        self._ble_timer = Clock.schedule_interval(self._tick_ble_label, 1)

    def show_qr(self, message=None):
        """
        No known device found OR first boot.
        Show QR + both action buttons.
        """
        self._stop_all_timers()
        self.status_label.text  = message or 'Scan QR code with\nMiniK app to pair'
        self.status_label.color = (0.9, 0.9, 0.9, 1)

        # Generate QR (safe to call multiple times - idempotent)
        if self.controller:
            self._generate_qr(self.controller.dm.get_device_id())

        self.qr_image.opacity    = 1

        # Pair button
        self.pair_btn.text       = 'Connect New\nPhone'
        self.pair_btn.opacity    = 1
        self.pair_btn.disabled   = False

        # Action button → scan mode
        self._action_btn_mode    = 'scan'
        self.action_btn.text     = 'Look for\nmy Phone'
        self.action_btn.opacity  = 1
        self.action_btn.disabled = False

    def show_error(self, message):
        self._stop_all_timers()
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
        print(f"[PAIRING] QR data: {qr_data}")

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
        self.qr_image.texture     = core_img.texture
        self.device_id_label.text = f"Device: {device_id}"
