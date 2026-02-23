import threading
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.clock import Clock


class CaptureScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.controller         = None
        self.preview_event      = None
        self._preview_scheduled = False  # Guard: FadeTransition fires on_enter twice
        self._build_ui()

    def _build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        title = Label(
            text='Capture Food Image',
            font_size='14sp',
            size_hint=(1, 0.1),
            bold=True
        )

        self.preview = Image(
            size_hint=(1, 0.7),
            allow_stretch=True,
            keep_ratio=True
        )

        button_box = BoxLayout(
            orientation='horizontal',
            size_hint=(1, 0.15),
            spacing=10
        )

        self.capture_btn = Button(
            text='Capture',
            background_color=(0.2, 0.6, 0.8, 1),
            font_size='13sp'
        )
        self.capture_btn.bind(on_press=self.on_capture)

        back_btn = Button(
            text='Back',
            background_color=(0.5, 0.5, 0.5, 1),
            font_size='13sp'
        )
        back_btn.bind(on_press=self.on_back)

        button_box.add_widget(self.capture_btn)
        button_box.add_widget(back_btn)

        self.status_label = Label(
            text='Position food item in frame',
            font_size='10sp',
            size_hint=(1, 0.05),
            color=(0.7, 0.7, 0.7, 1)
        )

        layout.add_widget(title)
        layout.add_widget(self.preview)
        layout.add_widget(button_box)
        layout.add_widget(self.status_label)

        self.add_widget(layout)

    # ── Lifecycle ──────────────────────────────────────

    def on_enter(self):
        # Always reset button state on enter — handles returning from result screen
        self.enable_capture()

        # Guard prevents double start from FadeTransition firing on_enter twice
        if not self._preview_scheduled:
            self._preview_scheduled = True
            Clock.schedule_once(lambda dt: self.start_preview(), 0.3)

    def on_leave(self):
        self._preview_scheduled = False  # Reset so next on_enter works
        self.stop_preview()

    # ── Camera Preview ─────────────────────────────────

    def start_preview(self):
        if self.preview_event:
            self.preview_event.cancel()
            self.preview_event = None

        if not self.controller:
            return

        try:
            self.controller.dm.hardware.start_camera_preview()
            self.preview_event = Clock.schedule_interval(
                self.update_preview, 1.0 / 10  # 10 FPS — enough for Pi Zero 2W
            )
            self.status_label.text  = 'Position food item in frame'
            self.status_label.color = (0.7, 0.7, 0.7, 1)
            print("[CAPTURE] Preview started")
        except Exception as e:
            import traceback
            print(f"[CAPTURE] Camera preview error: {e}")
            traceback.print_exc()
            self.status_label.text  = 'Camera unavailable'
            self.status_label.color = (1, 0.3, 0.3, 1)

    def update_preview(self, dt):
        if not self.controller:
            return
        try:
            texture = self.controller.dm.hardware.get_preview_texture()
            if texture:
                self.preview.texture = texture
        except Exception:
            pass  # Frame drop is acceptable

    def stop_preview(self):
        if self.preview_event:
            self.preview_event.cancel()
            self.preview_event = None
        if self.controller:
            try:
                self.controller.dm.hardware.stop_camera_preview()
                print("[CAPTURE] Preview stopped")
            except Exception as e:
                print(f"[CAPTURE] Stop preview error: {e}")

    # ── Button Handlers ────────────────────────────────

    def on_capture(self, instance):
        if not self.controller:
            return
        # Disable immediately to block double-tap
        self.capture_btn.disabled = True
        self.status_label.text    = 'Capturing...'
        self.status_label.color   = (0.9, 0.9, 0.9, 1)

        # Defer 1 frame so Kivy redraws button release state before blocking work
        Clock.schedule_once(lambda dt: self._do_capture(), 0.1)

    def _do_capture(self):
        """Stop preview then hand off to controller in a background thread."""
        self.stop_preview()
        threading.Thread(target=self._capture_worker, daemon=True).start()

    def _capture_worker(self):
        """Blocking capture runs in background — never touch widgets directly."""
        try:
            # controller.capture_image() is the existing method — reuse it
            # but we own the button state here, not the controller
            image_path = self.controller.dm.hardware.capture_image()
            if image_path:
                Clock.schedule_once(
                    lambda dt: self._on_capture_success(image_path), 0
                )
            else:
                Clock.schedule_once(
                    lambda dt: self.show_error('Capture failed — try again'), 0
                )
                Clock.schedule_once(lambda dt: self._after_capture(), 0.5)
        except Exception as e:
            Clock.schedule_once(
                lambda dt: self.show_error(f'Error: {e}'), 0
            )
            Clock.schedule_once(lambda dt: self._after_capture(), 0.5)

    def _on_capture_success(self, image_path):
        """Runs on main thread after successful capture."""
        self.status_label.text  = 'Image captured!'
        self.status_label.color = (0.3, 1, 0.3, 1)
        # Delegate rest of flow (send to phone / mock) to controller
        self.controller.on_image_captured(image_path)

    def _after_capture(self):
        """Always re-enable button and restart preview — failure recovery path."""
        self.enable_capture()
        self.start_preview()

    def on_back(self, instance):
        self.stop_preview()
        self.manager.current = 'home'

    # ── State Control ──────────────────────────────────

    def disable_capture(self):
        self.capture_btn.disabled = True
        self.status_label.text    = 'Sending to phone...'
        self.status_label.color   = (0.9, 0.9, 0.9, 1)

    def enable_capture(self):
        self.capture_btn.disabled = False
        self.status_label.text    = 'Position food item in frame'
        self.status_label.color   = (0.7, 0.7, 0.7, 1)

    def show_error(self, message):
        self.status_label.text  = message
        self.status_label.color = (1, 0.3, 0.3, 1)
