import os
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout

class PairingScreen(Screen):
    def on_enter(self):
        layout = BoxLayout(orientation="vertical", padding=50, spacing=20)

        label = Label(text="Pair this device with your phone")
        btn = Button(text="Paired", size_hint=(.5, .4), pos_hint={"center_x": 0.5, "center_y": .5})

        btn.bind(on_press=lambda x: self.go_home())

        layout.add_widget(label)
        layout.add_widget(btn)

        self.clear_widgets()
        self.add_widget(layout)

    def go_home(self):
        self.manager.current = "home"
