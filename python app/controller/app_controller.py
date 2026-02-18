from kivy.clock import Clock
from threading import Thread
import time


class AppController:
    """Main application controller managing state and business logic"""
    
    def __init__(self, screen_manager, device_manager):
        self.sm = screen_manager
        self.dm = device_manager
        self.voc_ready = False
        self.priming_check_event = None
        self.ble_timeout_event = None
        self.current_test_data = {}
        
    def on_app_start(self):
        """Initialize on app start"""
        # Start hardware initialization
        Thread(target=self.dm.hardware.initialize, daemon=True).start()
        
    def cleanup(self):
        """Cleanup before app closes"""
        self.dm.cleanup()
        if self.priming_check_event:
            self.priming_check_event.cancel()
        if self.ble_timeout_event:
            self.ble_timeout_event.cancel()
    
    # Pairing Screen Actions
    def start_pairing(self):
        """Start BLE pairing process"""
        screen = self.sm.get_screen('pairing')
        screen.show_qr_code()
        
        # Start BLE advertising
        success = self.dm.network.start_ble_advertising()
        if not success:
            screen.show_error("Failed to start BLE")
            return
        
        # Set timeout for BLE (2-3 minutes)
        self.ble_timeout_event = Clock.schedule_once(
            lambda dt: self.stop_ble_pairing(),
            180  # 3 minutes
        )
        
        # Listen for pairing in background
        Thread(target=self._wait_for_pairing, daemon=True).start()
    
    def _wait_for_pairing(self):
        """Background thread to wait for pairing"""
        result = self.dm.network.wait_for_pairing()
        if result:
            Clock.schedule_once(lambda dt: self._on_paired(result), 0)
    
    def _on_paired(self, credentials):
        """Called when device is successfully paired"""
        if self.ble_timeout_event:
            self.ble_timeout_event.cancel()
        
        # Save pairing info
        self.dm.save_pairing(credentials)
        
        # Connect to WiFi
        wifi_success = self.dm.network.connect_wifi(
            credentials['ssid'],
            credentials['password']
        )
        
        if wifi_success:
            # Stop BLE and switch to WiFi mode
            self.dm.network.stop_ble()
            self.dm.network.start_wifi_server()
            
            # Navigate to home screen
            self.sm.current = 'home'
        else:
            screen = self.sm.get_screen('pairing')
            screen.show_error("WiFi connection failed")
    
    def stop_ble_pairing(self):
        """Stop BLE pairing after timeout"""
        self.dm.network.stop_ble()
        screen = self.sm.get_screen('pairing')
        screen.hide_qr_code()
    
    # Home Screen Actions
    def start_test(self):
        """Start spoilage test"""
        # Check if VOC sensors are ready
        if not self.dm.hardware.are_voc_sensors_ready():
            screen = self.sm.get_screen('home')
            screen.show_waiting_message()
            
            # Start priming sensors
            self.dm.hardware.start_voc_priming()
            
            # Check periodically if sensors are ready
            self.priming_check_event = Clock.schedule_interval(
                self._check_voc_ready,
                2.0  # Check every 2 seconds
            )
        else:
            # Sensors ready, go to capture
            self.sm.current = 'capture'
            self.sm.get_screen('capture').start_preview()
    
    def _check_voc_ready(self, dt):
        """Periodically check if VOC sensors are ready"""
        if self.dm.hardware.are_voc_sensors_ready():
            if self.priming_check_event:
                self.priming_check_event.cancel()
            
            screen = self.sm.get_screen('home')
            screen.hide_waiting_message()
            
            # Navigate to capture screen
            self.sm.current = 'capture'
            self.sm.get_screen('capture').start_preview()
    
    # Capture Screen Actions
    # Capture Screen Actions
    def capture_image(self):
        """Capture image and send to phone"""
        screen = self.sm.get_screen('capture')
        screen.disable_capture()
    
    # Run in background thread so UI doesn't freeze during capture
        Thread(target=self._do_capture, daemon=True).start()

    def _do_capture(self):
        """Background capture + network logic"""
        screen = self.sm.get_screen('capture')
    
        # Capture image
        image_path = self.dm.hardware.capture_image()
        if not image_path:
            Clock.schedule_once(
                lambda dt: screen.show_error("Failed to capture image"), 0
            )
            Clock.schedule_once(lambda dt: screen.enable_capture(), 0)
            return
    
        self.current_test_data['image_path'] = image_path
        print(f"[CONTROLLER] Image captured: {image_path}")
    
        import config
    
        if config.USE_REAL_NETWORK:
            # Real flow: send to phone, wait for CNN result
            success = self.dm.network.send_image_to_phone(image_path)
            if success:
                Clock.schedule_once(lambda dt: setattr(self.sm, 'current', 'analyzing'), 0)
                Thread(target=self._wait_for_cnn_result, daemon=True).start()
            else:
                Clock.schedule_once(
                    lambda dt: screen.show_error("Failed to send image"), 0
                )
                Clock.schedule_once(lambda dt: screen.enable_capture(), 0)
        else:
            # Mock mode: skip network entirely, use default sensors, go to reading
            print("[CONTROLLER] Mock network - skipping CNN, using default sensors")
            self.current_test_data['food_type'] = 'Unknown'
            self.current_test_data['sensors_to_read'] = ['MQ2', 'MQ3', 'MQ135']
        
        Clock.schedule_once(lambda dt: self._proceed_to_reading(), 0)

    def _proceed_to_reading(self):
         """Navigate to sensor reading screen"""
         self.sm.current = 'reading'
         screen = self.sm.get_screen('reading')
         screen.set_sensors(self.current_test_data['sensors_to_read'])
         Thread(target=self._read_voc_sensors, daemon=True).start()

    
    def _wait_for_cnn_result(self):
        """Wait for CNN processing result from phone"""
        result = self.dm.network.wait_for_cnn_result()
        if result:
            Clock.schedule_once(
                lambda dt: self._on_cnn_result_received(result),
                0
            )
    
    def _on_cnn_result_received(self, result):
        """Process CNN result"""
        food_type = result.get('food_type')
        sensors_to_read = result.get('sensors', [])
        
        self.current_test_data['food_type'] = food_type
        self.current_test_data['sensors_to_read'] = sensors_to_read
        
        # Move to reading screen
        self.sm.current = 'reading'
        screen = self.sm.get_screen('reading')
        screen.set_sensors(sensors_to_read)
        
        # Start reading sensors
        Thread(target=self._read_voc_sensors, daemon=True).start()
    
    def _read_voc_sensors(self):
        """Read VOC sensors + environmental data and send"""
        sensors = self.current_test_data.get('sensors_to_read', [])

        # Read all sensor data (VOC + temperature + humidity)
        all_data = self.dm.hardware.read_all_sensor_data(sensors)

        # Generate CSV
        csv_path = self.dm.hardware.generate_sensor_csv(all_data)

        import config

        if config.USE_REAL_NETWORK:
            # Real flow: send CSV to phone, wait for ML result
            success = self.dm.network.send_csv_to_phone(csv_path)
            if success:
                result = self.dm.network.wait_for_ml_result()
                if result:
                    Clock.schedule_once(lambda dt: self._show_result(result), 0)
            else:
                print("[CONTROLLER] Failed to send CSV to phone")
        else:
            # Mock mode: generate a fake result and show it directly
            print("[CONTROLLER] Mock network - generating mock ML result")
            import random
            mock_result = {
                'status': random.choice(['Fresh', 'Moderate', 'Spoiled']),
                'confidence': round(random.uniform(75, 99), 1),
                'food_type': self.current_test_data.get('food_type', 'Unknown'),
                'details': 'Mock analysis result'
            }
            # Small delay to simulate processing
            time.sleep(1)
            Clock.schedule_once(lambda dt: self._show_result(mock_result), 0) 
            
    def _show_result(self, result):
        """Display final result"""
        self.sm.current = 'result'
        screen = self.sm.get_screen('result')
        screen.display_result(result)
    
    # Result Screen Actions
    def test_again(self):
        """Start a new test"""
        self.current_test_data = {}
        self.sm.current = 'home'
    
    def shutdown_device(self):
        """Turn off the device"""
        self.dm.shutdown()


