from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

class HomeScreen(Screen):
    def on_enter(self):
        layout = BoxLayout(orientation="vertical")

        title = Label(text="Food Analyzer", font_size=32)
        start_btn = Button(text="Start Analysis", size_hint=(1, 0.3))

        start_btn.bind(on_press=self.start)

        layout.add_widget(title)
        layout.add_widget(start_btn)

        self.clear_widgets()
        self.add_widget(layout)

    def start(self, instance):
        self.manager.current = "camera"
