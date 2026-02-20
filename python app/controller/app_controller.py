from kivy.clock import Clock
from threading import Thread
import time
import os


class AppController:
    """Main application controller managing state and business logic"""

    def __init__(self, screen_manager, device_manager):
        self.sm  = screen_manager
        self.dm  = device_manager
        self.priming_check_event = None
        self.ble_timeout_event   = None
        self.current_test_data   = {}

    def on_app_start(self):
        """Initialize hardware on app start"""
        Thread(target=self.dm.hardware.initialize, daemon=True).start()

    def cleanup(self):
        """Cleanup before app closes"""
        self.dm.cleanup()
        if self.priming_check_event:
            self.priming_check_event.cancel()
        if self.ble_timeout_event:
            self.ble_timeout_event.cancel()

    # ──────────────────────────────────────────────────
    # Pairing Screen
    # ──────────────────────────────────────────────────

    def start_pairing(self):
        """Start BLE pairing process"""
        screen = self.sm.get_screen('pairing')
        screen.show_qr_code()

        success = self.dm.network.start_ble_advertising()
        if not success:
            screen.show_error("Failed to start BLE")
            return

        self.ble_timeout_event = Clock.schedule_once(
            lambda dt: self.stop_ble_pairing(), 180
        )
        Thread(target=self._wait_for_pairing, daemon=True).start()

    def _wait_for_pairing(self):
        result = self.dm.network.wait_for_pairing()
        if result:
            Clock.schedule_once(lambda dt: self._on_paired(result), 0)

    def _on_paired(self, credentials):
        if self.ble_timeout_event:
            self.ble_timeout_event.cancel()

        self.dm.save_pairing(credentials)

        wifi_success = self.dm.network.connect_wifi(
            credentials['ssid'],
            credentials['password']
        )

        if wifi_success:
            self.dm.network.stop_ble()
            self.dm.network.start_wifi_server()
            self.sm.current = 'home'
        else:
            self.sm.get_screen('pairing').show_error("WiFi connection failed")

    def stop_ble_pairing(self):
        self.dm.network.stop_ble()
        self.sm.get_screen('pairing').hide_qr_code()

    def reset_pairing(self):
        """Reset pairing data - dev/testing use"""
        self.dm.reset_pairing()
        print("[CONTROLLER] Pairing reset")
        self.sm.get_screen('pairing').reset_ui()

    # ──────────────────────────────────────────────────
    # Home Screen
    # ──────────────────────────────────────────────────

    def start_test(self):
        """Start spoilage test - check sensors first"""
        if not self.dm.hardware.are_voc_sensors_ready():
            screen = self.sm.get_screen('home')
            screen.show_waiting_message()
            self.dm.hardware.start_voc_priming()
            self.priming_check_event = Clock.schedule_interval(
                self._check_voc_ready, 2.0
            )
        else:
            self.sm.current = 'capture'
            self.sm.get_screen('capture').start_preview()

    def _check_voc_ready(self, dt):
        if self.dm.hardware.are_voc_sensors_ready():
            if self.priming_check_event:
                self.priming_check_event.cancel()
            self.sm.get_screen('home').hide_waiting_message()
            self.sm.current = 'capture'
            self.sm.get_screen('capture').start_preview()

    # ──────────────────────────────────────────────────
    # Capture Screen
    # ──────────────────────────────────────────────────

    def capture_image(self):
        """Disable UI and start capture in background thread"""
        self.sm.get_screen('capture').disable_capture()
        Thread(target=self._do_capture, daemon=True).start()

    def _do_capture(self):
        """Background: capture image then route based on network mode"""
        screen = self.sm.get_screen('capture')

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
            # Real flow:
            #   Send image → wait for CNN result (confirms cloud receipt) → delete
            success = self.dm.network.send_image_to_phone(image_path)
            if success:
                Clock.schedule_once(
                    lambda dt: setattr(self.sm, 'current', 'analyzing'), 0
                )
                Thread(target=self._wait_for_cnn_result, daemon=True).start()
            else:
                Clock.schedule_once(
                    lambda dt: screen.show_error("Failed to send image"), 0
                )
                Clock.schedule_once(lambda dt: screen.enable_capture(), 0)
        else:
            # Mock flow: simulate confirmed cloud receipt, delete, skip to reading
            print("[CONTROLLER] Mock network - skipping CNN, using default sensors")
            self.current_test_data['food_type']        = 'Unknown'
            self.current_test_data['sensors_to_read']  = ['MQ2', 'MQ3', 'MQ135']
            self._delete_image(image_path)
            Clock.schedule_once(lambda dt: self._proceed_to_reading(), 0)

    def _wait_for_cnn_result(self):
        result = self.dm.network.wait_for_cnn_result()
        if result:
            Clock.schedule_once(
                lambda dt: self._on_cnn_result_received(result), 0
            )

    def _on_cnn_result_received(self, result):
        """
        CNN result = cloud confirmed it received and processed the image.
        Safe to delete the local copy now.
        """
        self.current_test_data['food_type']       = result.get('food_type')
        self.current_test_data['sensors_to_read'] = result.get('sensors', [])

        # Delete only after cloud confirmation
        image_path = self.current_test_data.get('image_path')
        if image_path:
            self._delete_image(image_path)

        self._proceed_to_reading()

    def _proceed_to_reading(self):
        """Navigate to sensor reading screen and begin reading"""
        self.sm.current = 'reading'
        screen = self.sm.get_screen('reading')
        screen.set_sensors(self.current_test_data['sensors_to_read'])
        Thread(target=self._read_voc_sensors, daemon=True).start()

    # ──────────────────────────────────────────────────
    # Sensor Reading
    # ──────────────────────────────────────────────────

    def _read_voc_sensors(self):
        """Read VOC + environment sensors, send CSV, get ML result"""
        sensors  = self.current_test_data.get('sensors_to_read', [])
        all_data = self.dm.hardware.read_all_sensor_data(sensors)
        csv_path = self.dm.hardware.generate_sensor_csv(all_data)

        import config

        if config.USE_REAL_NETWORK:
            success = self.dm.network.send_csv_to_phone(csv_path)
            if success:
                result = self.dm.network.wait_for_ml_result()
                if result:
                    Clock.schedule_once(
                        lambda dt: self._show_result(result), 0
                    )
                else:
                    print("[CONTROLLER] No ML result received from phone")
            else:
                print("[CONTROLLER] Failed to send CSV to phone")
        else:
            # Mock: generate a fake ML result
            print("[CONTROLLER] Mock network - generating mock ML result")
            import random
            mock_result = {
                'status':     random.choice(['Fresh', 'Moderate', 'Spoiled']),
                'confidence': round(random.uniform(75, 99), 1),
                'food_type':  self.current_test_data.get('food_type', 'Unknown'),
                'details':    'Mock analysis result'
            }
            time.sleep(1)  # Simulate processing
            Clock.schedule_once(lambda dt: self._show_result(mock_result), 0)

    # ──────────────────────────────────────────────────
    # Result Screen
    # ──────────────────────────────────────────────────

    def _show_result(self, result):
        self.sm.current = 'result'
        self.sm.get_screen('result').display_result(result)

    def test_again(self):
        self.current_test_data = {}
        self.sm.current = 'home'

    def shutdown_device(self):
        self.dm.shutdown()

    # ──────────────────────────────────────────────────
    # Utilities
    # ──────────────────────────────────────────────────

    def _delete_image(self, image_path):
        """
        Delete image from Pi storage.
        Called only after cloud confirms receipt via CNN result,
        or in mock mode after simulated send.
        CleanupManager handles any edge-case leftovers hourly.
        """
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
                print(f"[CONTROLLER] Image deleted: {os.path.basename(image_path)}")
        except Exception as e:
            print(f"[CONTROLLER] Could not delete image: {e}")
