from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button

class ResultScreen(Screen):
    def on_enter(self):
        layout = BoxLayout(orientation="vertical")

        result = Label(text="Result: Fresh", font_size=28)
        again = Button(text="Scan Again")

        again.bind(on_press=lambda x: self.go_home())

        layout.add_widget(result)
        layout.add_widget(again)

        self.clear_widgets()
        self.add_widget(layout)

    def go_home(self):
        self.manager.current = "home"
