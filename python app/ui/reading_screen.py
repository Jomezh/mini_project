from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.graphics import Color, Rectangle


class ReadingSensorsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.controller = None
        self.build_ui()
        
    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=15, spacing=10)
        
        # Title
        title = Label(
            text='Reading VOC Sensors',
            font_size='16sp',
            bold=True,
            size_hint=(1, 0.15)
        )
        
        # Sensors list container
        self.sensors_container = GridLayout(
            cols=1,
            size_hint=(1, 0.7),
            spacing=8,
            padding=10
        )
        
        # Status
        self.status_label = Label(
            text='Please wait...',
            font_size='12sp',
            color=(0.7, 0.7, 0.7, 1),
            size_hint=(1, 0.15)
        )
        
        layout.add_widget(title)
        layout.add_widget(self.sensors_container)
        layout.add_widget(self.status_label)
        
        self.add_widget(layout)
    
    def set_sensors(self, sensors):
        """Display which sensors are being read"""
        self.sensors_container.clear_widgets()
        
        for sensor in sensors:
            sensor_label = Label(
                text=f'• {sensor}',
                font_size='13sp',
                size_hint=(1, None),
                height=30,
                halign='left'
            )
            sensor_label.bind(size=sensor_label.setter('text_size'))
            self.sensors_container.add_widget(sensor_label)
