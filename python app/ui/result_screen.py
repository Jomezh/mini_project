from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock


class ResultScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.controller       = None
        self._auto_home_evt   = None
        self._pending_home    = None   # FIX: initialise so _on_go_home never crashes
        self._auto_home_countdown = 0
        self.build_ui()

    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)

        self.title_label = Label(
            text='Test Result',
            font_size='18sp',
            bold=True,
            size_hint=(1, 0.10),
        )

        # ── Result area ───────────────────────────────────────────────────
        result_box = BoxLayout(
            orientation='vertical',
            size_hint=(1, 0.48),
            spacing=8,
        )

        self.food_type_label = Label(
            text='',
            font_size='15sp',
            bold=True,
            size_hint=(1, 0.25),
            halign='center', valign='middle',
        )
        self.food_type_label.bind(size=self.food_type_label.setter('text_size'))

        self.freshness_label = Label(
            text='',
            font_size='24sp',
            bold=True,
            size_hint=(1, 0.40),
            halign='center', valign='middle',
        )
        self.freshness_label.bind(size=self.freshness_label.setter('text_size'))

        self.confidence_label = Label(
            text='',
            font_size='12sp',
            color=(0.7, 0.7, 0.7, 1),
            size_hint=(1, 0.20),
            halign='center', valign='middle',
        )
        self.confidence_label.bind(size=self.confidence_label.setter('text_size'))

        self.source_label = Label(
            text='',
            font_size='11sp',
            color=(0.55, 0.55, 0.55, 1),
            size_hint=(1, 0.15),
            halign='center', valign='middle',
        )
        self.source_label.bind(size=self.source_label.setter('text_size'))

        result_box.add_widget(self.food_type_label)
        result_box.add_widget(self.freshness_label)
        result_box.add_widget(self.confidence_label)
        result_box.add_widget(self.source_label)

        # ── Buttons ───────────────────────────────────────────────────────
        button_box = BoxLayout(
            orientation='horizontal',
            size_hint=(1, .5),
            spacing=10,
        )

        self.test_again_btn = Button(
            text='Test Again',
            background_color=(0.2, 0.7, 0.3, 1),
            font_size='15sp',
        )
        self.test_again_btn.bind(on_press=self._on_test_again)

        self.home_btn = Button(
            text='Go Home',
            background_color=(0.2, 0.45, 0.75, 1),
            font_size='13sp',
            opacity=0,
            disabled=True,
        )
        self.home_btn.bind(on_press=self._on_go_home)

        self.shutdown_btn = Button(
            text='Turn Off Device',
            background_color=(0.7, 0.2, 0.2, 1),
            font_size='15sp',
        )
        self.shutdown_btn.bind(on_press=self._on_shutdown)

        button_box.add_widget(self.test_again_btn)
        button_box.add_widget(self.home_btn)
        button_box.add_widget(self.shutdown_btn)

        layout.add_widget(self.title_label)
        layout.add_widget(result_box)
        layout.add_widget(button_box)
        self.add_widget(layout)

    # ── Called by app_controller ──────────────────────────────────────────

    def display_result(self, result):
        """Normal result — food identified, freshness returned."""
        self._cancel_auto_home()

        food_type = result.get('food_type', 'Unknown')

        # FIX: RF sends 'status', check it first — 'freshness' is legacy fallback
        freshness = result.get('status', result.get('freshness', 'Unknown'))

        # FIX: confidence arrives as float (RF) OR string (CNN) — normalise both
        raw_conf = result.get('confidence', 0)
        try:
            confidence = float(raw_conf)
        except (ValueError, TypeError):
            confidence = 0.0

        details = result.get('details', '')

        self.title_label.text      = 'Test Result'
        self.title_label.color     = (1, 1, 1, 1)
        self.food_type_label.text  = f'Food: {food_type.title()}'
        self.food_type_label.color = (1, 1, 1, 1)
        self.freshness_label.text  = self._display_label(freshness)
        self.confidence_label.text = f'Confidence: {confidence:.1f}%'
        self.source_label.text     = details

        # FIX: normalise before colour check — strip spaces/underscores
        # so 'HalfFresh', 'half_fresh', 'HALFFRESH' all match correctly
        upper = freshness.upper().replace(' ', '').replace('_', '')

        # FIX: check HALFFRESH before FRESH — 'FRESH' is a substring of 'HALFFRESH'
        if 'HALFFRESH' in upper or 'HALF' in upper or 'MODERATE' in upper:
            self.freshness_label.color = (1.0, 0.7, 0.2, 1)   # orange
        elif 'FRESH' in upper:
            self.freshness_label.color = (0.2, 0.8, 0.2, 1)   # green
        elif 'SPOILED' in upper or 'BAD' in upper or 'ROTTEN' in upper:
            self.freshness_label.color = (0.9, 0.2, 0.2, 1)   # red
        else:
            self.freshness_label.color = (0.7, 0.7, 0.7, 1)   # grey fallback

        self.test_again_btn.disabled = False
        self.test_again_btn.opacity  = 1
        self.home_btn.disabled       = True
        self.home_btn.opacity        = 0

    def display_no_match(self, on_home):
        """CNN could not identify a food — show message, auto-return home."""
        self._cancel_auto_home()
        self.title_label.text        = 'Not Recognised'
        self.title_label.color       = (1.0, 0.65, 0.2, 1)
        self.food_type_label.text    = 'No food detected in image'
        self.food_type_label.color   = (0.85, 0.85, 0.85, 1)
        self.freshness_label.text    = '—'
        self.freshness_label.color   = (0.5, 0.5, 0.5, 1)
        self.confidence_label.text   = 'Point the camera at the food and try again'
        self.source_label.text       = ''

        self.test_again_btn.disabled = True
        self.test_again_btn.opacity  = 0
        self.home_btn.disabled       = False
        self.home_btn.opacity        = 1
        self._pending_home           = on_home

        self._auto_home_countdown = 4
        self._update_home_btn_label()
        self._auto_home_evt = Clock.schedule_interval(self._tick_no_match, 1.0)

    # ── Internal helpers ──────────────────────────────────────────────────

    @staticmethod
    def _display_label(freshness: str) -> str:
        """Normalise RF/CNN label variants to human-readable display string."""
        key = freshness.upper().replace(' ', '').replace('_', '')
        if 'HALFFRESH' in key or 'HALF' in key or 'MODERATE' in key:
            return 'Half Fresh'
        if 'FRESH' in key:
            return 'Fresh'
        if 'SPOILED' in key or 'BAD' in key or 'ROTTEN' in key:
            return 'Spoiled'
        return freshness.title()

    def _cancel_auto_home(self):
        if self._auto_home_evt:
            self._auto_home_evt.cancel()
            self._auto_home_evt = None

    def _tick_no_match(self, dt):
        self._auto_home_countdown -= 1
        if self._auto_home_countdown <= 0:
            self._cancel_auto_home()
            if self._pending_home:
                self._pending_home()
            return False
        self._update_home_btn_label()

    def _update_home_btn_label(self):
        self.home_btn.text = f'Go Home ({self._auto_home_countdown}s)'

    # ── Button callbacks ──────────────────────────────────────────────────

    def _on_test_again(self, *args):
        self._cancel_auto_home()
        if self.controller:
            self.controller.test_again()

    def _on_go_home(self, *args):
        self._cancel_auto_home()
        if self._pending_home:
            self._pending_home()
        elif self.controller:
            self.controller.go_to_home()

    def _on_shutdown(self, *args):
        self._cancel_auto_home()
        if self.controller:
            self.controller.shutdown_device()
