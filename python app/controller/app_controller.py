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
        self.priming_check_event   = None
        self.ble_timeout_event     = None
        self.current_test_data     = {}
        self.current_connected_mac = None   # MAC of currently active device

    def on_app_start(self):
        Thread(target=self.dm.hardware.initialize, daemon=True).start()

    def cleanup(self):
        self.dm.cleanup()
        if self.priming_check_event:
            self.priming_check_event.cancel()
        if self.ble_timeout_event:
            self.ble_timeout_event.cancel()

    # ──────────────────────────────────────────────────
    # Navigation Helper
    # ──────────────────────────────────────────────────

    def _go_to_home(self):
        """
        Navigate to home screen and update connected device display.
        Always use this instead of setattr(sm, 'current', 'home').
        """
        if self.current_connected_mac:
            known = self.dm.get_known_devices()
            match = next(
                (d for d in known
                 if d['ble_mac'] == self.current_connected_mac),
                None
            )
            if match:
                home = self.sm.get_screen('home')
                home.set_connected_device(
                    match['ble_name'],
                    match.get('ssid', '')
                )
        self.sm.current = 'home'

    # ──────────────────────────────────────────────────
    # Pairing Screen
    # ──────────────────────────────────────────────────

    def start_pairing_screen(self):
        """
        Always called at boot.
        Known devices exist → scan BLE first.
        No known devices → show QR immediately.
        """
        screen = self.sm.get_screen('pairing')

        if self.dm.has_known_devices():
            screen.show_scanning()
            Thread(target=self._scan_for_known_device, daemon=True).start()
        else:
            screen.show_qr()

    def _scan_for_known_device(self):
        """BLE scan for any previously paired device"""
        try:
            found = self.dm.scan_for_known_devices(timeout=10)

            if found:
                # Phone is nearby - hotspot state unknown until WiFi attempt
                Clock.schedule_once(
                    lambda dt: self._auto_connect(found), 0
                )
            else:
                # No known device nearby - show QR
                Clock.schedule_once(
                    lambda dt: self.sm.get_screen('pairing').show_qr(), 0
                )
        except Exception as e:
            import traceback
            print(f"[CONTROLLER] !! Scan thread crash: {e}")
            traceback.print_exc()
            Clock.schedule_once(
                lambda dt: self.sm.get_screen('pairing').show_qr(
                    message="Scan failed - try again"
                ), 0
            )

    def _auto_connect(self, known_device):
        """Phone found via BLE - attempt WiFi/hotspot connect"""
        self.sm.get_screen('pairing').show_connecting(known_device['ble_name'])
        Thread(
            target=self._do_wifi_connect_with_retry,
            args=(known_device,),
            daemon=True
        ).start()

    def _do_wifi_connect_with_retry(self, known_device):
        """Crash-protected wrapper for auto-connect retry"""
        try:
            self._auto_connect_retry_logic(known_device)
        except Exception as e:
            import traceback
            print(f"[CONTROLLER] !! WiFi connect thread crash: {e}")
            traceback.print_exc()
            Clock.schedule_once(
                lambda dt: self.sm.get_screen('pairing').show_qr(
                    message=f"Connection error:\n{e}"
                ), 0
            )

    def _auto_connect_retry_logic(self, known_device):
        """
        Try to connect to saved hotspot.
        BLE confirmed phone is nearby so retries make sense.
        Notifies phone via BLE if hotspot is off.
        """
        ssid    = known_device['ssid']
        ble_mac = known_device['ble_mac']
        name    = known_device['ble_name']

        for attempt in range(1, WIFI_RETRY_LIMIT + 1):
            print(f"[CONTROLLER] WiFi attempt {attempt}/{WIFI_RETRY_LIMIT} "
                  f"for '{ssid}'")

            # password=None: nmcli uses saved credentials
            wifi_ok = self.dm.network.connect_wifi(ssid, password=None)
            print(f"[CONTROLLER] WiFi result: {wifi_ok}")

            if wifi_ok:
                self.current_connected_mac = ble_mac   # Track active device
                self.dm.update_last_connected(ble_mac)
                self.dm.network.start_wifi_server()
                print("[CONTROLLER] Auto-connect success → Home")
                Clock.schedule_once(lambda dt: self._go_to_home(), 0)
                return

            # Hotspot off - notify phone via BLE (BLE still alive)
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

        # All retries exhausted - password may have changed too
        Clock.schedule_once(
            lambda dt: self.sm.get_screen('pairing').show_qr(
                message=f"Could not reach hotspot on {name}.\n"
                        f"Hotspot password may have changed.\n"
                        f"Scan QR to re-pair."
            ), 0
        )

    def retry_wifi_now(self):
        """User tapped Retry Now on hotspot prompt"""
        self.sm.get_screen('pairing').show_scanning()
        Thread(target=self._scan_for_known_device, daemon=True).start()

    def rescan_for_devices(self):
        """User tapped Look for my Phone"""
        self.sm.get_screen('pairing').show_scanning()
        Thread(target=self._scan_for_known_device, daemon=True).start()

    def start_pairing(self):
        """User tapped Connect New Phone - start BLE advertising"""
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
        try:
            result = self.dm.network.wait_for_pairing()
            if result:
                Clock.schedule_once(lambda dt: self._on_paired(result), 0)
            else:
                Clock.schedule_once(
                    lambda dt: self.sm.get_screen('pairing').show_qr(
                        message="Pairing timed out - try again"
                    ), 0
                )
        except Exception as e:
            import traceback
            print(f"[CONTROLLER] !! Pairing wait crash: {e}")
            traceback.print_exc()
            Clock.schedule_once(
                lambda dt: self.sm.get_screen('pairing').show_qr(
                    message="Pairing error - try again"
                ), 0
            )

    def _on_paired(self, credentials):
        """Phone sent SSID + password via BLE. Save and connect."""
        if self.ble_timeout_event:
            self.ble_timeout_event.cancel()

        self.dm.save_pairing(credentials)

        Thread(
            target=self._do_new_pair_wifi_connect,
            args=(credentials,),
            daemon=True
        ).start()

    def _do_new_pair_wifi_connect(self, credentials):
        """Crash-protected wrapper for new-pair WiFi connect"""
        try:
            self._new_pair_wifi_logic(credentials)
        except Exception as e:
            import traceback
            print(f"[CONTROLLER] !! New pair WiFi crash: {e}")
            traceback.print_exc()
            Clock.schedule_once(
                lambda dt: self.sm.get_screen('pairing').show_qr(
                    message=f"Connection error:\n{e}"
                ), 0
            )

    def _new_pair_wifi_logic(self, credentials):
        """
        WiFi connect after fresh BLE pairing.
        Retries because user may enable hotspot after sending credentials.
        """
        ssid     = credentials['ssid']
        password = credentials['password']
        ble_mac  = credentials.get('ble_mac', '')
        name     = credentials.get('ble_name', 'your phone')

        for attempt in range(1, WIFI_RETRY_LIMIT + 1):
            print(f"[CONTROLLER] New pair WiFi attempt {attempt}/{WIFI_RETRY_LIMIT}")

            wifi_ok = self.dm.network.connect_wifi(ssid, password)
            print(f"[CONTROLLER] WiFi result: {wifi_ok}")

            if wifi_ok:
                self.current_connected_mac = ble_mac   # Track active device

                # Send Pi IP back to phone via BLE before closing it
                pi_ip = self.dm.network.get_local_ip()
                if pi_ip:
                    self.dm.network.send_ip_to_phone(pi_ip)

                time.sleep(1)   # Let phone read IP characteristic

                self.dm.network.stop_ble()
                self.dm.network.start_wifi_server()

                print("[CONTROLLER] New pair complete → Home")
                Clock.schedule_once(lambda dt: self._go_to_home(), 0)
                return

            # Hotspot off - notify phone via BLE (still connected)
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
        """Dev only - wipes ALL known devices"""
        self.dm.reset_pairing()
        self.current_connected_mac = None
        self.sm.get_screen('pairing').show_qr()
        print("[CONTROLLER] All pairing data cleared")

    def forget_device(self):
        """
        Forget ONLY the currently connected device.
        Other known devices are untouched.
        """
        if self.current_connected_mac:
            # Find name for log message
            known = self.dm.get_known_devices()
            match = next(
                (d for d in known
                 if d['ble_mac'] == self.current_connected_mac),
                None
            )
            name = match['ble_name'] if match else self.current_connected_mac
            self.dm.remove_device(self.current_connected_mac)
            self.current_connected_mac = None
            print(f"[CONTROLLER] Forgot device: {name}")
        else:
            print("[CONTROLLER] forget_device: no active device to forget")

        # Go back to pairing and re-run boot logic
        self.sm.current = 'pairing'
        Clock.schedule_once(
            lambda dt: self.start_pairing_screen(), 0.3
        )

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
        try:
            self._capture_logic()
        except Exception as e:
            import traceback
            print(f"[CONTROLLER] !! Capture thread crash: {e}")
            traceback.print_exc()
            screen = self.sm.get_screen('capture')
            Clock.schedule_once(
                lambda dt: screen.show_error(f"Capture error: {e}"), 0
            )
            Clock.schedule_once(lambda dt: screen.enable_capture(), 0)

    def _capture_logic(self):
        screen     = self.sm.get_screen('capture')
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
        try:
            result = self.dm.network.wait_for_cnn_result()
            if result:
                Clock.schedule_once(
                    lambda dt: self._on_cnn_result_received(result), 0
                )
        except Exception as e:
            print(f"[CONTROLLER] !! CNN result thread crash: {e}")

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
        try:
            self._sensor_read_logic()
        except Exception as e:
            import traceback
            print(f"[CONTROLLER] !! Sensor read thread crash: {e}")
            traceback.print_exc()

    def _sensor_read_logic(self):
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
                print(f"[CONTROLLER] Image deleted: "
                      f"{os.path.basename(image_path)}")
        except Exception as e:
            print(f"[CONTROLLER] Could not delete image: {e}")
