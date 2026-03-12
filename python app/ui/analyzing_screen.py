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
        self.controller    = None
        self._anim         = None
        self._status_tick  = None
        self._pending_home = None
        self.build_ui()

    def build_ui(self):
        # Preserve original layout structure exactly — only add cancel btn at bottom
        layout = BoxLayout(orientation='vertical', padding=30, spacing=20)

        layout.add_widget(Label(size_hint=(1, 0.2)))

        title = Label(
            text='Analyzing Image',
            font_size='18sp',
            bold=True,
            size_hint=(1, 0.15),
        )

        self.progress = ProgressBar(
            max=100, value=0, size_hint=(1, 0.1)
        )

        self.status_label = Label(
            text='Sending image to phone...',
            font_size='13sp',
            color=(0.7, 0.7, 0.7, 1),
            size_hint=(1, 0.15),
            halign='center', valign='middle',
        )
        self.status_label.bind(size=self.status_label.setter('text_size'))

        # title_label kept as ref so timeout state can change text/color
        self.title_label = title

        layout.add_widget(Label(size_hint=(1, 0.4)))
        layout.add_widget(title)
        layout.add_widget(self.progress)
        layout.add_widget(self.status_label)

        # Cancel button — height=0 means it takes NO space when hidden
        # Reused for both "cancel" and "timeout go home" states
        self.cancel_btn = Button(
            text='Cancel & Go Home',
            background_color=(0.55, 0.1, 0.1, 1),
            font_size='11sp',
            size_hint=(1, None),
            height=0,
            opacity=0,
            disabled=True,
        )
        self.cancel_btn.bind(on_press=self._on_action_btn)
        layout.add_widget(self.cancel_btn)

        self.add_widget(layout)

    # ── Kivy lifecycle ────────────────────────────────────────────────────

    def on_enter(self):
        self._reset_state()
        # Progress bar ping-pong animation
        self._anim = Animation(value=100, duration=2.0)
        self._anim.repeat = True
        self._anim.start(self.progress)
        # Cycle status messages every 6s so user knows it's alive
        self._status_idx      = 0
        self._status_messages = [
            'Sending image to phone...',
            'CNN model identifying food...',
            'Waiting for classification...',
            'Almost there...',
        ]
        self._status_tick = Clock.schedule_interval(self._cycle_status, 6.0)

    def on_leave(self):
        self._stop_all()

    # ── Internal ──────────────────────────────────────────────────────────

    def _reset_state(self):
        self.title_label.text        = 'Analyzing Image'
        self.title_label.color       = (1, 1, 1, 1)
        self.status_label.text       = 'Sending image to phone...'
        self.status_label.color      = (0.7, 0.7, 0.7, 1)
        self.progress.value          = 0
        self.cancel_btn.text         = 'Cancel & Go Home'
        self.cancel_btn.background_color = (0.55, 0.1, 0.1, 1)
        self.cancel_btn.height       = 0
        self.cancel_btn.opacity      = 0
        self.cancel_btn.disabled     = True
        self._pending_home           = None

    def _stop_all(self):
        if self._anim:
            Animation.cancel_all(self.progress)
            self._anim = None
        if self._status_tick:
            self._status_tick.cancel()
            self._status_tick = None

    def _cycle_status(self, dt):
        self._status_idx     = (self._status_idx + 1) % len(self._status_messages)
        self.status_label.text = self._status_messages[self._status_idx]

    def _show_cancel(self):
        """Expand the button into view — takes real space only when visible."""
        self.cancel_btn.height   = 44
        self.cancel_btn.opacity  = 1
        self.cancel_btn.disabled = False

    # ── Called by app_controller ──────────────────────────────────────────

    def show_cancel_btn(self):
        """Revealed after 35s of waiting."""
        self.status_label.text  = 'This is taking longer than usual...'
        self.status_label.color = (1.0, 0.75, 0.3, 1)
        self._show_cancel()

    def show_timeout_message(self, on_home):
        """Called when 120s hard timeout fires."""
        self._stop_all()
        self._pending_home               = on_home
        self.title_label.text            = 'Analysis Timed Out'
        self.title_label.color           = (1.0, 0.4, 0.4, 1)
        self.status_label.text           = 'No response from phone.\nCheck connection and try again.'
        self.status_label.color          = (0.85, 0.85, 0.85, 1)
        self.cancel_btn.text             = 'Go Home'
        self.cancel_btn.background_color = (0.2, 0.45, 0.75, 1)
        self._show_cancel()

    # ── Button handler ────────────────────────────────────────────────────

    def _on_action_btn(self, *args):
        if self.cancel_btn.text == 'Go Home':
            if self._pending_home:
                self._pending_home()
        else:
            if self.controller:
                self.controller.cancel_analysis()
