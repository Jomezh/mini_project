from kivy.app import App
from kivy.uix.screenmanager import ScreenManager

from ui.pairing import PairingScreen
from ui.home import HomeScreen
from ui.camera import CameraScreen
from ui.loading import LoadingScreen
from ui.result import ResultScreen

class FoodAnalyzerApp(App):
    def build(self):
        sm = ScreenManager()

        sm.add_widget(PairingScreen(name="pairing"))
        sm.add_widget(HomeScreen(name="home"))
        sm.add_widget(CameraScreen(name="camera"))
        sm.add_widget(LoadingScreen(name="loading"))
        sm.add_widget(ResultScreen(name="result"))

        # initial state
        sm.current = "pairing"
        return sm

if __name__ == "__main__":
    FoodAnalyzerApp().run()
