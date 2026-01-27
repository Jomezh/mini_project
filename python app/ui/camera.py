from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

class CameraScreen(Screen):
    def on_enter(self):
        layout = BoxLayout(orientation="vertical")

        preview = Label(text="[ Camera Preview ]", font_size=24)
        capture_btn = Button(text="Capture")

        capture_btn.bind(on_press=self.capture)

        layout.add_widget(preview)
        layout.add_widget(capture_btn)

        self.clear_widgets()
        self.add_widget(layout)

    def capture(self, instance):
        self.manager.current = "loading"
