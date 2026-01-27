from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label

class CameraScreen(Screen):
    def on_enter(self):
        layout = BoxLayout(orientation="vertical", padding=50, spacing=20)

        preview = Label(text="[ Camera Preview ]", font_size=24)
        capture_btn = Button(text="Capture", size_hint=(.5, .4), pos_hint={"center_x": 0.5, "center_y": .5})

        capture_btn.bind(on_press=self.capture)

        layout.add_widget(preview)
        layout.add_widget(capture_btn)

        self.clear_widgets()
        self.add_widget(layout)

    def capture(self, instance):
        self.manager.current = "loading"
