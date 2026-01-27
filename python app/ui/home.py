from kivy.uix.label import Label 
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.lang import Builder

import os

Builder.load_file(os.path.join(os.path.dirname(__file__), 'round.kv'))


class HomeScreen(Screen):
    def on_enter(self):
        layout = BoxLayout(orientation="vertical", padding=50, spacing=20, )

        title = Label(text="Food Analyzer", font_size=32)
        start_btn = Button(text="Start Analysis",size_hint=(.25, 0.25), pos_hint={"center_x": 0.5, "center_y": 0.5})
        shutdown_btn = Button(text='[b]Power\n OFF[/b]', size_hint=(.125, .125), pos_hint={"center_x": 0.90, "center_y": 0.75}, markup=True)
        
        start_btn.bind(on_press=self.start)
        shutdown_btn.bind(on_press=lambda x: os.system("sudo shutdown now"))

        layout.add_widget(title)
        layout.add_widget(start_btn)
        layout.add_widget(shutdown_btn)

        self.clear_widgets()
        self.add_widget(layout)

    def start(self, instance):
        self.manager.current = "camera"

    def shutdown(self, instance):
        os.system("sudo shutdown now")


