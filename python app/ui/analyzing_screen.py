from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.animation import Animation
from kivy.clock import Clock


class AnalyzingScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.controller   = None
        self._anim        = None
        self._status_tick = None
        self.build_ui()

    def build_ui(self):
        self.layout = BoxLayout(orientation='vertical', padding=30, spacing=20)

        self.layout.add_widget(Label(size_hint=(1, 0.15)))

        self.title_label = Label(
            text='Analyzing Image',
            font_size='18sp',
            bold=True,
            size_hint=(1, 0.12),
        )

        self.progress = ProgressBar(
            max=100, value=0, size_hint=(1, 0.08)
        )

        self.status_label = Label(
            text='Sending image to phone...',
            font_size='13sp',
            color=(0.7, 0.7, 0.7, 1),
            size_hint=(1, 0.12),
            halign='center', valign='middle',
        )
        self.status_label.bind(size=self.status_label.setter('text_size'))

        # Cancel button — hidden until 35s elapsed
        self.cancel_btn = Button(
            text='Cancel & Go Home',
            background_color=(0.55, 0.1, 0.1, 1),
            font_size='11sp',
            size_hint=(1, 0.18),
            opacity=0,
            disabled=True,
        )
        self.cancel_btn.bind(on_press=self._on_cancel)

        # Timeout / error label — hidden by default
        self.timeout_label = Label(
            text='',
            font_size='12sp',
            color=(1.0, 0.4, 0.4, 1),
            size_hint=(1, 0.10),
            halign='center', valign='middle',
            opacity=0,
        )
        self.timeout_label.bind(size=self.timeout_label.setter('text_size'))

        self.home_btn = Button(
            text='Go Home',
            background_color=(0.2, 0.45, 0.75, 1),
            font_size='11sp',
            size_hint=(1, 0.18),
            opacity=0,
            disabled=True,
        )
        self.home_btn.bind(on_press=self._on_go_home)

        self.layout.add_widget(self.title_label)
        self.layout.add_widget(self.progress)
        self.layout.add_widget(self.status_label)
        self.layout.add_widget(Label(size_hint=(1, 0.07)))
        self.layout.add_widget(self.cancel_btn)
        self.layout.add_widget(self.timeout_label)
        self.layout.add_widget(self.home_btn)
        self.layout.add_widget(Label(size_hint=(1, 0.0)))

        self.add_widget(self.layout)

    # ── Kivy lifecycle ────────────────────────────────────────────────────

    def on_enter(self):
        self._reset_ui()
        # Looping progress animation
        self._anim = Animation(value=100, duration=2.0)
        self._anim.repeat = True
        self._anim.start(self.progress)
        # Cycle status messages so the user knows it's alive
        self._status_messages = [
            'Sending image to phone...',
            'CNN model identifying food...',
            'Waiting for classification...',
            'Almost there...',
        ]
        self._status_idx  = 0
        self._status_tick = Clock.schedule_interval(self._cycle_status, 6.0)

    def on_leave(self):
        self._stop_animations()

    # ── Internal helpers ──────────────────────────────────────────────────

    def _reset_ui(self):
        self.title_label.text           = 'Analyzing Image'
        self.title_label.color          = (1, 1, 1, 1)
        self.status_label.text          = 'Sending image to phone...'
        self.status_label.color         = (0.7, 0.7, 0.7, 1)
        self.progress.value             = 0
        self.progress.opacity           = 1
        self.cancel_btn.opacity         = 0
        self.cancel_btn.disabled        = True
        self.timeout_label.text         = ''
        self.timeout_label.opacity      = 0
        self.home_btn.opacity           = 0
        self.home_btn.disabled          = True

    def _stop_animations(self):
        if self._anim:
            Animation.cancel_all(self.progress)
            self._anim = None
        if self._status_tick:
            self._status_tick.cancel()
            self._status_tick = None

    def _cycle_status(self, dt):
        self._status_idx = (self._status_idx + 1) % len(self._status_messages)
        self.status_label.text = self._status_messages[self._status_idx]

    # ── Called by app_controller ──────────────────────────────────────────

    def show_cancel_btn(self):
        """Revealed after 35s — user feels something is wrong by then."""
        self.status_label.text    = 'This is taking longer than usual...'
        self.status_label.color   = (1.0, 0.75, 0.3, 1)
        self.cancel_btn.opacity   = 1
        self.cancel_btn.disabled  = False

    def show_timeout_message(self, on_home):
        """Called when wait_for_cnn_result times out naturally (120s)."""
        self._stop_animations()
        self.progress.opacity       = 0
        self.title_label.text       = 'Analysis Timed Out'
        self.title_label.color      = (1.0, 0.4, 0.4, 1)
        self.status_label.text      = 'No response from phone.\nCheck your connection and try again.'
        self.status_label.color     = (0.85, 0.85, 0.85, 1)
        self.cancel_btn.opacity     = 0
        self.cancel_btn.disabled    = True
        self.timeout_label.text     = 'Analysis timed out'
        self.timeout_label.opacity  = 1
        self.home_btn.opacity       = 1
        self.home_btn.disabled      = False
        self._pending_home          = on_home

    # ── Button callbacks ──────────────────────────────────────────────────

    def _on_cancel(self, *args):
        if self.controller:
            self.controller.cancel_analysis()

    def _on_go_home(self, *args):
        if hasattr(self, '_pending_home') and self._pending_home:
            self._pending_home()
