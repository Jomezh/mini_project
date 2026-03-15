from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock


class ReadingSensorsScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.controller       = None
        self._warmup_tick     = None
        self._warmup_total    = 30
        self._warmup_rem_fn   = None
        self.build_ui()

    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=25, spacing=12)
        layout.add_widget(Label(size_hint=(1, 0.08)))

        self.title_label = Label(
            text='Reading Sensors',
            font_size='18sp', bold=True,
            size_hint=(1, 0.14),
        )
        self.phase_label = Label(
            text='Preparing...',
            font_size='13sp', bold=True,
            color=(1.0, 0.85, 0.35, 1),
            size_hint=(1, 0.12),
            halign='center', valign='middle',
        )
        self.phase_label.bind(size=self.phase_label.setter('text_size'))

        self.progress = ProgressBar(max=100, value=0, size_hint=(1, 0.07))

        self.count_label = Label(
            text='',
            font_size='11sp', color=(0.55, 0.55, 0.55, 1),
            size_hint=(1, 0.10),
            halign='center', valign='middle',
        )
        self.count_label.bind(size=self.count_label.setter('text_size'))

        self.sensors_label = Label(
            text='',
            font_size='12sp', color=(0.65, 0.85, 0.65, 1),
            size_hint=(1, 0.49),
            halign='center', valign='top',
        )
        self.sensors_label.bind(size=self.sensors_label.setter('text_size'))

        for w in [self.title_label, self.phase_label,
                  self.progress, self.count_label, self.sensors_label]:
            layout.add_widget(w)
        self.add_widget(layout)

    # ── Called by controller ──────────────────────────────────────────────────

    def set_sensors(self, sensors):
        lines = '\n'.join(f'  • {s}' for s in sensors)
        lines += '\n  • DHT11  (Temperature / Humidity)'
        self.sensors_label.text = lines
        self.phase_label.text   = 'Warming up sensors...'
        self.phase_label.color  = (1.0, 0.85, 0.35, 1)
        self.progress.value     = 0
        self.count_label.text   = ''

    def start_warmup_display(self, warmup_remaining_fn, total_secs=30):
        self._warmup_rem_fn = warmup_remaining_fn
        self._warmup_total  = total_secs
        self._stop_warmup_tick()
        self._warmup_tick = Clock.schedule_interval(self._tick_warmup, 1.0)
        self._tick_warmup(0)

    def _tick_warmup(self, dt):
        remaining = self._warmup_rem_fn()
        if remaining <= 0:
            self._stop_warmup_tick()
            self.phase_label.text  = 'Sensors ready — starting measurement'
            self.phase_label.color = (0.35, 0.9, 0.35, 1)
            self.progress.value    = 100
            self.count_label.text  = ''
            return False
        pct = max(0, min(100, (1 - remaining / self._warmup_total) * 100))
        self.progress.value    = pct
        self.phase_label.text  = 'Warming up sensors...'
        self.phase_label.color = (1.0, 0.85, 0.35, 1)
        self.count_label.text  = f'{int(remaining)}s remaining'

    def _stop_warmup_tick(self):
        if self._warmup_tick:
            self._warmup_tick.cancel()
            self._warmup_tick = None

    def update_sample_progress(self, sample_idx, total_samples):
        self._stop_warmup_tick()
        pct = (sample_idx / total_samples) * 100
        self.progress.value    = pct
        self.phase_label.text  = f'Collecting readings  ({int(pct)}%)'
        self.phase_label.color = (0.4, 0.75, 1.0, 1)
        self.count_label.text  = f'Sample {sample_idx} / {total_samples}'
        if sample_idx >= total_samples:
            self.phase_label.text  = 'Computing features...'
            self.phase_label.color = (0.7, 0.5, 1.0, 1)
            self.count_label.text  = 'mean  /  std  /  max  per sensor'

    def on_leave(self):
        self._stop_warmup_tick()
