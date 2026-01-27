from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button

class ResultScreen(Screen):
    def on_enter(self):
        layout = BoxLayout(orientation="vertical", padding=50, spacing=20)

        result = Label(text="Result: Fresh", font_size=28)
        again = Button(text="Scan Again", size_hint=(.5, .4), pos_hint={"center_x": 0.5, "center_y": .5})

        again.bind(on_press=lambda x: self.go_home())

        layout.add_widget(result)
        layout.add_widget(again)

        self.clear_widgets()
        self.add_widget(layout)

    def go_home(self):
        self.manager.current = "home"
