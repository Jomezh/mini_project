from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label


class ResultScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.controller = None
        self.build_ui()
        
    def build_ui(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        # Title
        title = Label(
            text='Test Result',
            font_size='18sp',
            bold=True,
            size_hint=(1, 0.15)
        )
        
        # Result container
        result_box = BoxLayout(
            orientation='vertical',
            size_hint=(1, 0.5),
            spacing=10
        )
        
        self.food_type_label = Label(
            text='',
            font_size='15sp',
            bold=True,
            size_hint=(1, 0.3)
        )
        
        self.freshness_label = Label(
            text='',
            font_size='20sp',
            bold=True,
            size_hint=(1, 0.4)
        )
        
        self.confidence_label = Label(
            text='',
            font_size='12sp',
            color=(0.7, 0.7, 0.7, 1),
            size_hint=(1, 0.3)
        )
        
        result_box.add_widget(self.food_type_label)
        result_box.add_widget(self.freshness_label)
        result_box.add_widget(self.confidence_label)
        
        # Buttons
        button_box = BoxLayout(
            orientation='vertical',
            size_hint=(1, 0.3),
            spacing=10
        )
        
        test_again_btn = Button(
            text='Test Again',
            background_color=(0.2, 0.7, 0.3, 1),
            font_size='15sp'
        )
        test_again_btn.bind(on_press=self.on_test_again)
        
        shutdown_btn = Button(
            text='Turn Off Device',
            background_color=(0.7, 0.2, 0.2, 1),
            font_size='15sp'
        )
        shutdown_btn.bind(on_press=self.on_shutdown)
        
        button_box.add_widget(test_again_btn)
        button_box.add_widget(shutdown_btn)
        
        layout.add_widget(title)
        layout.add_widget(result_box)
        layout.add_widget(button_box)
        
        self.add_widget(layout)
    
    def display_result(self, result):
        """Display the test result"""
        food_type = result.get('food_type', 'Unknown')
        freshness = result.get('freshness', 'Unknown')
        confidence = result.get('confidence', 0)
        
        self.food_type_label.text = f'Food: {food_type}'
        self.freshness_label.text = freshness.upper()
        self.confidence_label.text = f'Confidence: {confidence:.1f}%'
        
        # Color code based on freshness
        if 'FRESH' in freshness.upper():
            self.freshness_label.color = (0.2, 0.8, 0.2, 1)
        elif 'SPOILED' in freshness.upper() or 'BAD' in freshness.upper():
            self.freshness_label.color = (0.9, 0.2, 0.2, 1)
        else:
            self.freshness_label.color = (1, 0.7, 0.2, 1)
    
    def on_test_again(self, instance):
        if self.controller:
            self.controller.test_again()
    
    def on_shutdown(self, instance):
        if self.controller:
            self.controller.shutdown_device()
