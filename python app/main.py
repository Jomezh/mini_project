import os
import sys
from threading import Thread, Event

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.core.window import Window
from kivy.config import Config
from kivy.clock import Clock

import config
config.print_config()

Config.set('graphics', 'width',      '240')
Config.set('graphics', 'height',     '320')
Config.set('graphics', 'fullscreen', '0')
Config.set('graphics', 'resizable',  False)
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

Window.clearcolor = (0.1, 0.1, 0.1, 1)


class MiniKApp(App):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from utils.device_manager import DeviceManager
        self.device_manager = DeviceManager()
        self.controller     = None
        self.screen_manager = None
        self._hw_ready      = Event()

    def build(self):
        from ui.pairing_screen   import PairingScreen
        from ui.home_screen      import HomeScreen
        from ui.capture_screen   import CaptureScreen
        from ui.analyzing_screen import AnalyzingScreen
        from ui.reading_screen   import ReadingSensorsScreen
        from ui.result_screen    import ResultScreen

        self.title = 'MiniK - VOC Detection System'

        self.screen_manager = ScreenManager(transition=FadeTransition())
        self.screen_manager.add_widget(PairingScreen(name='pairing'))
        self.screen_manager.add_widget(HomeScreen(name='home'))
        self.screen_manager.add_widget(CaptureScreen(name='capture'))
        self.screen_manager.add_widget(AnalyzingScreen(name='analyzing'))
        self.screen_manager.add_widget(ReadingSensorsScreen(name='reading'))
        self.screen_manager.add_widget(ResultScreen(name='result'))

        from controller.app_controller import AppController
        self.controller = AppController(
            self.screen_manager,
            self.device_manager
        )

        # Assign controller to ALL screens before any navigation
        for screen in self.screen_manager.screens:
            screen.controller = self.controller

        self.screen_manager.current = 'pairing'
        return self.screen_manager

    def on_start(self):
        # Hardware init in background - pairing screen starts when ready
        Thread(target=self._init_hardware, daemon=True).start()
        Clock.schedule_interval(self._check_hw_ready, 0.2)

    def _init_hardware(self):
        """
        Single hardware init entry point.
        on_app_start() already starts hardware.initialize() in its own thread.
        Do NOT call hardware.initialize() directly here - causes double init.
        """
        try:
            self.controller.on_app_start()
        except Exception as e:
            import traceback
            print(f"[MAIN] Hardware init error: {e}")
            traceback.print_exc()
        finally:
            # Always signal ready - app must not hang if init fails
            self._hw_ready.set()

    def _check_hw_ready(self, dt):
        """Poll every 0.2s - start pairing screen as soon as hardware is ready"""
        if not hasattr(self, '_hw_wait_elapsed'):
            self._hw_wait_elapsed = 0.0

        self._hw_wait_elapsed += dt
        hw_done   = self._hw_ready.is_set()
        timed_out = self._hw_wait_elapsed >= 5.0

        if hw_done or timed_out:
            if timed_out and not hw_done:
                print("[MAIN] Hardware init timeout - proceeding anyway")
            Clock.unschedule(self._check_hw_ready)
            self.controller.start_pairing_screen()

    def on_stop(self):
        try:
            self.controller.cleanup()
        except Exception as e:
            print(f"[MAIN] Cleanup error: {e}")
        return True


if __name__ == '__main__':
    try:
        MiniKApp().run()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
