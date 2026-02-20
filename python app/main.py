import os
import sys
from threading import Thread

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
        self.controller = None
        self.screen_manager = None

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

        for screen in self.screen_manager.screens:
            screen.controller = self.controller

        # ── Determine starting screen ──────────────────────
        if self.device_manager.is_paired():
            if config.USE_REAL_NETWORK:
                # Show pairing screen while checking connection
                self.screen_manager.current = 'pairing'
                pairing = self.screen_manager.get_screen('pairing')
                pairing.show_checking_connection()
                Thread(target=self._verify_boot_connection, daemon=True).start()
            else:
                # Mock mode - skip check, go home
                self.screen_manager.current = 'home'
        else:
            self.screen_manager.current = 'pairing'

        return self.screen_manager

    def _verify_boot_connection(self):
        """Background boot connection verification"""
        result = self.device_manager.verify_connection_on_boot()

        if result is True:
            Clock.schedule_once(
                lambda dt: setattr(self.screen_manager, 'current', 'home'), 0
            )
        elif result == 'wifi_only':
            def go_home_warn(dt):
                self.screen_manager.current = 'home'
                self.screen_manager.get_screen('home').show_warning(
                    "Phone not reachable - check mobile app"
                )
            Clock.schedule_once(go_home_warn, 0)
        else:
            # Connection lost - force re-pair
            Clock.schedule_once(
                lambda dt: setattr(self.screen_manager, 'current', 'pairing'), 0
            )

    def on_start(self):
        self.controller.on_app_start()

    def on_stop(self):
        self.controller.cleanup()
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
