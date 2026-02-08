import kivy
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from utils.state import AppState
from ui.pairing import PairingScreen
from ui.home import HomeScreen
from ui.camera import CameraScreen
from ui.loading import LoadingScreen
from ui.result import ResultScreen

class FoodAnalyzerApp(App):
    def build(self):
        sm = ScreenManager()

        sm.add_widget(PairingScreen(name=AppState.PAIRING.value))
        sm.add_widget(HomeScreen(name=AppState.HOME.value))
        sm.add_widget(CameraScreen(name=AppState.CAMERA.value))
        sm.add_widget(LoadingScreen(name=AppState.LOADING.value))
        sm.add_widget(ResultScreen(name=AppState.RESULT.value))
        # initial state
        sm.current = AppState.PAIRING.value
        return sm

if __name__ == "__main__":
    FoodAnalyzerApp().run()
