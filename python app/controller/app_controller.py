from kivy.clock import Clock
from threading import Thread
import time
import os


# Retry config for WiFi/hotspot connect
WIFI_RETRY_LIMIT    = 3    # Max attempts before giving up
WIFI_RETRY_INTERVAL = 10   # Seconds between retries


class AppController:
    """Main application controller managing state and business logic"""

    def __init__(self, screen_manager, device_manager):
        self.sm  = screen_manager
        self.dm  = device_manager
        self.priming_check_event = None
        self.ble_timeout_event   = None
        self.current_test_data   = {}

    def on_app_start(self):
        Thread(target=self.dm.hardware.initialize, daemon=True).start()

    def cleanup(self):
        self.dm.cleanup()
        if self.priming_check_event:
            self.priming_check_event.cancel()
        if self.ble_timeout_event:
            self.ble_timeout_event.cancel()

    # ──────────────────────────────────────────────────
    # Pairing Screen
    # ──────────────────────────────────────────────────

    def start_pairing_screen(self):
        """
        Always called at boot.
        If known devices exist → scan for them first.
        If none → show QR immediately.
        """
        screen = self.sm.get_screen('pairing')

        if self.dm.has_known_devices():
            screen.show_scanning()
            Thread(target=self._scan_for_known_device, daemon=True).start()
        else:
            # First ever boot - no history, go straight to QR
            screen.show_qr()

    def _scan_for_known_device(self):
        """BLE scan for any previously paired device (10s timeout)"""
        found = self.dm.scan_for_known_devices(timeout=10)

        if found:
            # BLE confirmed phone is nearby
            # Hotspot state is still unknown - will check during WiFi connect
            Clock.schedule_once(
                lambda dt: self._auto_connect(found), 0
            )
        else:
            # No known device nearby - show QR for new pairing
            Clock.schedule_once(
                lambda dt: self.sm.get_screen('pairing').show_qr(), 0
            )

    def _auto_connect(self, known_device):
        """Phone found via BLE - attempt WiFi connect"""
        self.sm.get_screen('pairing').show_connecting(known_device['ble_name'])
        Thread(
            target=self._do_wifi_connect_with_retry,
            args=(known_device,),
            daemon=True
        ).start()

    def _do_wifi_connect_with_retry(self, known_device):
        """
        Try to connect to phone's hotspot.
        BLE confirmed the phone is nearby so retries make sense.
        If hotspot is off, notify phone via BLE and wait for user to enable it.
        """
        ssid    = known_device['ssid']
        ble_mac = known_device['ble_mac']
        name    = known_device['ble_name']

        for attempt in range(1, WIFI_RETRY_LIMIT + 1):
            print(f"[CONTROLLER] WiFi attempt {attempt}/{WIFI_RETRY_LIMIT} "
                  f"for '{ssid}'")

            # password=None: nmcli uses saved credentials
            wifi_ok = self.dm.network.connect_wifi(ssid, password=None)

            if wifi_ok:
                self.dm.update_last_connected(ble_mac)
                self.dm.network.start_wifi_server()
                Clock.schedule_once(
                    lambda dt: setattr(self.sm, 'current', 'home'), 0
                )
                return

            # Hotspot is off - notify phone via BLE (BLE still alive)
            self.dm.network.notify_enable_hotspot()

            if attempt < WIFI_RETRY_LIMIT:
                Clock.schedule_once(
                    lambda dt, a=attempt: 
                        self.sm.get_screen('pairing').show_hotspot_prompt(
                            device_name=name,
                            attempt=a,
                            retries_left=WIFI_RETRY_LIMIT - a,
                            retry_in=WIFI_RETRY_INTERVAL
                        ), 0
                )
                time.sleep(WIFI_RETRY_INTERVAL)

        # All retries exhausted
        Clock.schedule_once(
            lambda dt: self.sm.get_screen('pairing').show_qr(
                message=f"Could not reach hotspot on {name}.\n"
                        f"Enable hotspot or scan to re-pair."
            ), 0
        )

    def retry_wifi_now(self):
        """User tapped Retry Now on hotspot prompt"""
        self.sm.get_screen('pairing').show_scanning()
        Thread(target=self._scan_for_known_device, daemon=True).start()

    def rescan_for_devices(self):
        """User tapped Scan Again on QR screen"""
        screen = self.sm.get_screen('pairing')
        screen.show_scanning()
        Thread(target=self._scan_for_known_device, daemon=True).start()

    def start_pairing(self):
        """User tapped Pair New Device - start BLE advertising"""
        screen = self.sm.get_screen('pairing')
        screen.show_waiting_ble()

        success = self.dm.network.start_ble_advertising()
        if not success:
            screen.show_qr(message="Failed to start BLE - try again")
            return

        self.ble_timeout_event = Clock.schedule_once(
            lambda dt: self._on_ble_pairing_timeout(), 180
        )
        Thread(target=self._wait_for_pairing, daemon=True).start()

    def _wait_for_pairing(self):
        result = self.dm.network.wait_for_pairing()
        if result:
            Clock.schedule_once(lambda dt: self._on_paired(result), 0)
        else:
            Clock.schedule_once(
                lambda dt: self.sm.get_screen('pairing').show_qr(
                    message="Pairing timed out - try again"
                ), 0
            )

    def _on_paired(self, credentials):
        """
        Phone sent SSID + password via BLE.
        BLE is still alive so we can notify about hotspot if needed.
        """
        if self.ble_timeout_event:
            self.ble_timeout_event.cancel()

        # Save to known_devices list
        self.dm.save_pairing(credentials)

        Thread(
            target=self._do_new_pair_wifi_connect,
            args=(credentials,),
            daemon=True
        ).start()

    def _do_new_pair_wifi_connect(self, credentials):
        """
        WiFi connect after fresh BLE pairing.
        User may have sent credentials before enabling hotspot, so retry.
        """
        ssid     = credentials['ssid']
        password = credentials['password']
        name     = credentials.get('ble_name', 'your phone')

        for attempt in range(1, WIFI_RETRY_LIMIT + 1):
            print(f"[CONTROLLER] New pair WiFi attempt {attempt}/{WIFI_RETRY_LIMIT}")

            wifi_ok = self.dm.network.connect_wifi(ssid, password)

            if wifi_ok:
                # Get Pi IP and send back via BLE before closing it
                pi_ip = self.dm.network.get_local_ip()
                if pi_ip:
                    self.dm.network.send_ip_to_phone(pi_ip)

                time.sleep(1)   # Let phone read IP characteristic

                self.dm.network.stop_ble()
                self.dm.network.start_wifi_server()
                Clock.schedule_once(
                    lambda dt: setattr(self.sm, 'current', 'home'), 0
                )
                return

            # Hotspot not on - notify phone via BLE (still connected)
            self.dm.network.notify_enable_hotspot()

            if attempt < WIFI_RETRY_LIMIT:
                Clock.schedule_once(
                    lambda dt, a=attempt:
                        self.sm.get_screen('pairing').show_hotspot_prompt(
                            device_name=name,
                            attempt=a,
                            retries_left=WIFI_RETRY_LIMIT - a,
                            retry_in=WIFI_RETRY_INTERVAL
                        ), 0
                )
                time.sleep(WIFI_RETRY_INTERVAL)

        # All retries failed
        Clock.schedule_once(
            lambda dt: self.sm.get_screen('pairing').show_qr(
                message="Please enable your phone's hotspot,\nthen scan again"
            ), 0
        )

    def _on_ble_pairing_timeout(self):
        self.dm.network.stop_ble()
        self.sm.get_screen('pairing').show_qr(
            message="Pairing timed out - try again"
        )

    def stop_ble_pairing(self):
        self.dm.network.stop_ble()
        self.sm.get_screen('pairing').show_qr()

    def reset_pairing(self):
        self.dm.reset_pairing()
        self.sm.get_screen('pairing').show_qr()
        print("[CONTROLLER] All pairing data cleared")

    # ──────────────────────────────────────────────────
    # Home Screen
    # ──────────────────────────────────────────────────

    def start_test(self):
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
        self.sm.get_screen('capture').disable_capture()
        Thread(target=self._do_capture, daemon=True).start()

    def _do_capture(self):
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
            print("[CONTROLLER] Mock - skipping CNN, using default sensors")
            self.current_test_data['food_type']       = 'Unknown'
            self.current_test_data['sensors_to_read'] = ['MQ2', 'MQ3', 'MQ135']
            self._delete_image(image_path)
            Clock.schedule_once(lambda dt: self._proceed_to_reading(), 0)

    def _wait_for_cnn_result(self):
        result = self.dm.network.wait_for_cnn_result()
        if result:
            Clock.schedule_once(
                lambda dt: self._on_cnn_result_received(result), 0
            )

    def _on_cnn_result_received(self, result):
        self.current_test_data['food_type']       = result.get('food_type')
        self.current_test_data['sensors_to_read'] = result.get('sensors', [])

        image_path = self.current_test_data.get('image_path')
        if image_path:
            self._delete_image(image_path)

        self._proceed_to_reading()

    def _proceed_to_reading(self):
        self.sm.current = 'reading'
        screen = self.sm.get_screen('reading')
        screen.set_sensors(self.current_test_data['sensors_to_read'])
        Thread(target=self._read_voc_sensors, daemon=True).start()

    # ──────────────────────────────────────────────────
    # Sensor Reading
    # ──────────────────────────────────────────────────

    def _read_voc_sensors(self):
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
                    print("[CONTROLLER] No ML result received")
            else:
                print("[CONTROLLER] Failed to send CSV")
        else:
            import random
            mock_result = {
                'status':     random.choice(['Fresh', 'Moderate', 'Spoiled']),
                'confidence': round(random.uniform(75, 99), 1),
                'food_type':  self.current_test_data.get('food_type', 'Unknown'),
                'details':    'Mock analysis result'
            }
            time.sleep(1)
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
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
                print(f"[CONTROLLER] Image deleted: {os.path.basename(image_path)}")
        except Exception as e:
            print(f"[CONTROLLER] Could not delete image: {e}")
