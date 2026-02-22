from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label


class HomeScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.controller = None
        self._build_ui()

    def _build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=12)

        # Title section
        title_box = BoxLayout(
            orientation='vertical',
            size_hint=(1, 0.22),
            spacing=5
        )

        title = Label(
            text='MiniK',
            font_size='24sp',
            bold=True,
            size_hint=(1, 0.6)
        )

        subtitle = Label(
            text='VOC based food spoilage\ndetection system',  # fixed \\n → \n
            font_size='11sp',
            color=(0.7, 0.7, 0.7, 1),
            size_hint=(1, 0.4),
            halign='center',
            valign='middle'
        )
        subtitle.bind(size=subtitle.setter('text_size'))

        title_box.add_widget(title)
        title_box.add_widget(subtitle)

        # Connected device name + SSID
        self.device_label = Label(
            text='',
            font_size='9sp',
            color=(0.4, 0.75, 0.4, 1),
            size_hint=(1, 0.08),
            halign='center',
            valign='middle'
        )
        self.device_label.bind(size=self.device_label.setter('text_size'))

        # Waiting for sensors message
        self.waiting_label = Label(
            text='',
            font_size='12sp',
            color=(1, 0.7, 0.3, 1),
            size_hint=(1, 0.15),
            opacity=0,
            halign='center',
            valign='middle'
        )
        self.waiting_label.bind(size=self.waiting_label.setter('text_size'))

        # Button section
        button_box = BoxLayout(
            orientation='horizontal',
            size_hint=(1, 0.35),
            spacing=10
        )

        self.forget_btn = Button(
            text='Forget\nDevice',          # fixed \\n → \n
            size_hint=(1, 1),
            background_color=(0.5, 0.3, 0.1, 1),
            font_size='11sp',
            halign='center'
        )
        self.forget_btn.bind(on_press=self.on_forget_device)

        self.start_test_btn = Button(
            text='Start Test',
            size_hint=(1, 1),
            background_color=(0.2, 0.7, 0.3, 1),
            font_size='15sp'
        )
        self.start_test_btn.bind(on_press=self.on_start_test)

        shutdown_btn = Button(
            text='Turn Off\nDevice',        # fixed \\n → \n
            size_hint=(1, 1),
            background_color=(0.7, 0.2, 0.2, 1),
            font_size='13sp',
            halign='center'
        )
        shutdown_btn.bind(on_press=self.on_shutdown)

        button_box.add_widget(self.forget_btn)
        button_box.add_widget(self.start_test_btn)
        button_box.add_widget(shutdown_btn)

        # WiFi status bar
        self.status_label = Label(
            text='Connected via WiFi',
            font_size='10sp',
            color=(0.5, 0.8, 0.5, 1),
            size_hint=(1, 0.08)
        )

        layout.add_widget(title_box)
        layout.add_widget(self.device_label)
        layout.add_widget(self.waiting_label)
        layout.add_widget(button_box)
        layout.add_widget(self.status_label)

        self.add_widget(layout)

    # ── Lifecycle ──────────────────────────────────────

    def on_enter(self):
        """Refresh connected device info every time screen is shown"""
        if not self.controller:
            return
        mac = self.controller.current_connected_mac
        if mac:
            known = self.controller.dm.get_known_devices()
            match = next(
                (d for d in known if d['ble_mac'] == mac), None
            )
            if match:
                self.set_connected_device(
                    match['ble_name'],
                    match.get('ssid', '')
                )
        else:
            self.device_label.text = ''

    # ── Public Methods ─────────────────────────────────

    def set_connected_device(self, ble_name, ssid=''):
        if ssid:
            self.device_label.text = f'{ble_name}  •  {ssid}'
        else:
            self.device_label.text = f'{ble_name}'

    def show_waiting_message(self):
        self.waiting_label.text      = 'Waiting for VOC sensors\nto heat up...'  # fixed
        self.waiting_label.opacity   = 1
        self.start_test_btn.disabled = True

    def hide_waiting_message(self):
        self.waiting_label.opacity   = 0
        self.start_test_btn.disabled = False

    # ── Button Handlers ────────────────────────────────

    def on_start_test(self, instance):
        if self.controller:
            self.controller.start_test()

    def on_forget_device(self, instance):
        if self.controller:
            self.controller.forget_device()

    def on_shutdown(self, instance):
        if self.controller:
            self.controller.shutdown_device()
