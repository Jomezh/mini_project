import os
import sys
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.core.window import Window
from kivy.config import Config
from kivy.clock import Clock
from utils.device_manager import DeviceManager
from ui.pairing_screen import PairingScreen
from ui.home_screen import HomeScreen
from ui.capture_screen import CaptureScreen
from ui.analyzing_screen import AnalyzingScreen
from ui.reading_screen import ReadingSensorsScreen
from ui.result_screen import ResultScreen
from controller.app_controller import AppController

# Configure for 240x320 display
Config.set('graphics', 'width', '240')
Config.set('graphics', 'height', '320')
Config.set('graphics', 'fullscreen', '0')  # Set to '1' for production
Config.set('graphics', 'resizable', False)
Config.set('kivy', 'keyboard_mode', 'systemandrequire')

# For touch calibration on XPT2046
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

Window.clearcolor = (0.1, 0.1, 0.1, 1)


class MiniKApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.device_manager = DeviceManager()
        self.controller = None
        self.screen_manager = None
        
    def build(self):
        self.title = "MiniK - VOC Detection System"
        
        # Create screen manager
        self.screen_manager = ScreenManager(transition=FadeTransition())
        
        # Add all screens
        self.screen_manager.add_widget(PairingScreen(name='pairing'))
        self.screen_manager.add_widget(HomeScreen(name='home'))
        self.screen_manager.add_widget(CaptureScreen(name='capture'))
        self.screen_manager.add_widget(AnalyzingScreen(name='analyzing'))
        self.screen_manager.add_widget(ReadingSensorsScreen(name='reading'))
        self.screen_manager.add_widget(ResultScreen(name='result'))
        
        # Initialize controller
        self.controller = AppController(
            self.screen_manager,
            self.device_manager
        )
        
        # Set controller reference in all screens
        for screen in self.screen_manager.screens:
            screen.controller = self.controller
            
        # Determine starting screen based on pairing status
        if self.device_manager.is_paired():
            self.screen_manager.current = 'home'
        else:
            self.screen_manager.current = 'pairing'
            
        return self.screen_manager
    
    def on_start(self):
        """Called when the application starts"""
        self.controller.on_app_start()
        
    def on_stop(self):
        """Called when the application is closing"""
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
        sys.exit(1)
