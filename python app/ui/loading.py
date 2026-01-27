from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.clock import Clock

class LoadingScreen(Screen):
    def on_enter(self):
        self.clear_widgets()
        self.add_widget(Label(text="Analyzing...", font_size=24))

        # simulate server delay
        Clock.schedule_once(self.done, 2)

    def done(self, dt):
        self.manager.current = "result"
