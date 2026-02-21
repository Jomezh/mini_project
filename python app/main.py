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
        self.controller     = None
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

        # Always start on pairing screen
        # Controller decides: auto-connect or show QR
        self.screen_manager.current = 'pairing'

        return self.screen_manager

    def on_start(self):
        self.controller.on_app_start()
        # Give hardware 1 second to init before pairing logic runs
        Clock.schedule_once(
            lambda dt: self.controller.start_pairing_screen(), 1
        )

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
