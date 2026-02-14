from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label


class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.controller = None
        self.build_ui()
        
    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # Title section
        title_box = BoxLayout(
            orientation='vertical',
            size_hint=(1, 0.3),
            spacing=5
        )
        
        title = Label(
            text='MiniK',
            font_size='24sp',
            bold=True,
            size_hint=(1, 0.6)
        )
        
        subtitle = Label(
            text='VOC based food spoilage\ndetection system',
            font_size='11sp',
            color=(0.7, 0.7, 0.7, 1),
            size_hint=(1, 0.4),
            halign='center'
        )
        subtitle.bind(size=subtitle.setter('text_size'))
        
        title_box.add_widget(title)
        title_box.add_widget(subtitle)
        
        # Status/Waiting message
        self.waiting_label = Label(
            text='',
            font_size='13sp',
            color=(1, 0.7, 0.3, 1),
            size_hint=(1, 0.2),
            opacity=0
        )
        
        # Button section
        button_box = BoxLayout(
            orientation='vertical',
            size_hint=(1, 0.4),
            spacing=15
        )
        
        self.start_test_btn = Button(
            text='Start Test',
            size_hint=(1, 0.5),
            background_color=(0.2, 0.7, 0.3, 1),
            font_size='16sp'
        )
        self.start_test_btn.bind(on_press=self.on_start_test)
        
        shutdown_btn = Button(
            text='Turn Off Device',
            size_hint=(1, 0.5),
            background_color=(0.7, 0.2, 0.2, 1),
            font_size='16sp'
        )
        shutdown_btn.bind(on_press=self.on_shutdown)
        
        button_box.add_widget(self.start_test_btn)
        button_box.add_widget(shutdown_btn)
        
        # Connection status
        self.status_label = Label(
            text='Connected via WiFi',
            font_size='11sp',
            color=(0.5, 0.8, 0.5, 1),
            size_hint=(1, 0.1)
        )
        
        layout.add_widget(title_box)
        layout.add_widget(self.waiting_label)
        layout.add_widget(button_box)
        layout.add_widget(self.status_label)
        
        self.add_widget(layout)
    
    def on_start_test(self, instance):
        if self.controller:
            self.controller.start_test()
    
    def show_waiting_message(self):
        """Show waiting for VOC sensors message"""
        self.waiting_label.text = 'Waiting for VOC sensors\nto heat up...'
        self.waiting_label.opacity = 1
        self.start_test_btn.disabled = True
    
    def hide_waiting_message(self):
        """Hide waiting message"""
        self.waiting_label.opacity = 0
        self.start_test_btn.disabled = False
    
    def on_shutdown(self, instance):
        if self.controller:
            self.controller.shutdown_device()
