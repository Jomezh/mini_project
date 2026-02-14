from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.animation import Animation


class AnalyzingScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.controller = None
        self.build_ui()
        
    def build_ui(self):
        layout = BoxLayout(
            orientation='vertical',
            padding=30,
            spacing=20
        )
        
        # Spacer
        layout.add_widget(Label(size_hint=(1, 0.2)))
        
        # Title
        title = Label(
            text='Analyzing Image',
            font_size='18sp',
            bold=True,
            size_hint=(1, 0.15)
        )
        
        # Progress bar
        self.progress = ProgressBar(
            max=100,
            value=0,
            size_hint=(1, 0.1)
        )
        
        # Status message
        self.status_label = Label(
            text='Identifying food type...',
            font_size='13sp',
            color=(0.7, 0.7, 0.7, 1),
            size_hint=(1, 0.15)
        )
        
        # Spacer
        layout.add_widget(Label(size_hint=(1, 0.4)))
        
        layout.add_widget(title)
        layout.add_widget(self.progress)
        layout.add_widget(self.status_label)
        
        self.add_widget(layout)
    
    def on_enter(self):
        """Start animation when screen is entered"""
        # Animate progress bar
        anim = Animation(value=100, duration=2.0)
        anim.repeat = True
        anim.start(self.progress)
