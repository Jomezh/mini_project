from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout

class PairingScreen(Screen):
    def on_enter(self):
        layout = BoxLayout(orientation="vertical")

        label = Label(text="Pair this device with your phone")
        btn = Button(text="Paired")

        btn.bind(on_press=lambda x: self.go_home())

        layout.add_widget(label)
        layout.add_widget(btn)

        self.clear_widgets()
        self.add_widget(layout)

    def go_home(self):
        self.manager.current = "home"
