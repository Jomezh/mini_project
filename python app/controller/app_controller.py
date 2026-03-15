from kivy.clock import Clock
from threading import Thread, Event
import time
import os

WIFI_RETRY_LIMIT         = 3
WIFI_RETRY_INTERVAL      = 10
WIFI_FIRST_HOTSPOT_WAIT  = 25


class AppController:

    def __init__(self, screen_manager, device_manager):
        self.sm                    = screen_manager
        self.dm                    = device_manager
        self.priming_check_event   = None
        self.ble_timeout_event     = None
        self.current_test_data     = {}
        self.current_connected_mac = None
        self._wifi_cancel          = Event()
        self._cnn_cancel           = Event()
        self._cnn_timeout_event    = None
        self._pairing_in_progress  = False
        self._wifi_connected       = False
        self._current_ssid         = None
        self._connection_time      = 0.0

    def on_app_start(self):
        Thread(target=self.dm.hardware.initialize, daemon=True).start()
        Thread(target=self.dm.network.start_wifi_server, daemon=True).start()

    def cleanup(self):
        self.dm.cleanup()
        if self.priming_check_event:
            self.priming_check_event.cancel()
        if self.ble_timeout_event:
            self.ble_timeout_event.cancel()
        if self._cnn_timeout_event:
            self._cnn_timeout_event.cancel()

    def cancel_wifi_connect(self):
        self._wifi_cancel.set()

    # ── Navigation ────────────────────────────────────────────────────────────

    def go_to_home(self):
        if self.current_connected_mac:
            known = self.dm.get_known_devices()
            match = next(
                (d for d in known if d['ble_mac'] == self.current_connected_mac), None
            )
            if match:
                home = self.sm.get_screen('home')
                home.set_connected_device(
                    match['ble_name'], match.get('ssid', '')
                )
        self.sm.current = 'home'

    # ── Boot flow ─────────────────────────────────────────────────────────────

    def start_pairing_screen(self):
        screen = self.sm.get_screen('pairing')
        if self.dm.has_known_devices():
            screen.show_scanning()
            Thread(target=self.scan_for_known_device, daemon=True).start()
        else:
            screen.show_qr()

    # ── BLE scan / auto-connect ───────────────────────────────────────────────

    def scan_for_known_device(self):
        try:
            found = self.dm.scan_for_known_devices(timeout=10)
            if found:
                Clock.schedule_once(lambda dt: self.auto_connect(found), 0)
            else:
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

    def auto_connect(self, known_device):
        self.sm.get_screen('pairing').show_connecting(known_device['ble_name'])
        Thread(
            target=self.do_wifi_connect_with_retry,
            args=(known_device,),
            daemon=True
        ).start()

    def do_wifi_connect_with_retry(self, known_device):
        try:
            self.autoconnect_retry_logic(known_device)
        except Exception as e:
            import traceback
            print(f"[CONTROLLER] !! WiFi connect thread crash: {e}")
            traceback.print_exc()
            err = str(e)
            Clock.schedule_once(
                lambda dt: self.sm.get_screen('pairing').show_qr(
                    message=f"Connection error: {err}"
                ), 0
            )

    def autoconnect_retry_logic(self, known_device):
        ssid   = known_device['ssid']
        blemac = known_device['ble_mac']
        name   = known_device['ble_name']

        self._wifi_cancel.clear()

        for attempt in range(1, WIFI_RETRY_LIMIT + 1):
            if self._wifi_cancel.is_set():
                print("[CONTROLLER] Auto-connect cancelled")
                return

            print(f"[CONTROLLER] WiFi attempt {attempt}/{WIFI_RETRY_LIMIT} for {ssid}")
            self.dm.network.notify_enable_hotspot()

            wait         = WIFI_FIRST_HOTSPOT_WAIT if attempt == 1 else WIFI_RETRY_INTERVAL
            retries_left = WIFI_RETRY_LIMIT - attempt

            Clock.schedule_once(
                lambda dt, a=attempt, rl=retries_left, w=wait:
                    self.sm.get_screen('pairing').show_hotspot_prompt(
                        device_name=name, attempt=a,
                        retries_left=rl, retry_in=w
                    ), 0
            )

            cancelled = self._wifi_cancel.wait(timeout=wait)
            if cancelled:
                print("[CONTROLLER] Auto-connect cancelled during wait")
                return
            if self._wifi_cancel.is_set():
                return

            Clock.schedule_once(
                lambda dt: self.sm.get_screen('pairing').show_connecting(name), 0
            )

            wifiok = self.dm.network.connect_wifi(ssid, password=None)
            print(f"[CONTROLLER] WiFi result: {wifiok}")

            if wifiok:
                self._connection_time      = time.time()
                self.current_connected_mac = blemac
                self._wifi_connected       = True
                self._current_ssid         = ssid
                self.dm.update_last_connected(blemac)
                self.dm.start_heartbeat_after_wifi(
                    on_disconnected=self.on_phone_disconnected
                )
                print("[CONTROLLER] Auto-connect success → Home")
                Clock.schedule_once(lambda dt: self.go_to_home(), 0)
                return

        Clock.schedule_once(
            lambda dt: self.sm.get_screen('pairing').show_qr(
                message=(
                    f"Could not reach hotspot on {name}.\n"
                    f"Hotspot password may have changed.\n"
                    f"Scan QR to re-pair."
                )
            ), 0
        )

    def retry_wifi_now(self):
        self.sm.get_screen('pairing').show_scanning()
        Thread(target=self.scan_for_known_device, daemon=True).start()

    def rescan_for_devices(self):
        self.sm.get_screen('pairing').show_scanning()
        Thread(target=self.scan_for_known_device, daemon=True).start()

    # ── New BLE pairing flow ──────────────────────────────────────────────────

    def start_pairing(self):
        self.cancel_wifi_connect()
        screen  = self.sm.get_screen('pairing')
        screen.show_waiting_ble()
        success = self.dm.network.start_ble_advertising()
        if not success:
            screen.show_qr(message="Failed to start BLE - try again")
            return
        self.ble_timeout_event = Clock.schedule_once(
            lambda dt: self.on_ble_pairing_timeout(), 180
        )
        Thread(target=self.wait_for_pairing, daemon=True).start()

    def wait_for_pairing(self):
        try:
            result = self.dm.network.wait_for_pairing()
            if result:
                Clock.schedule_once(lambda dt: self.on_paired(result), 0)
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

    def on_paired(self, credentials):
        if self.ble_timeout_event:
            self.ble_timeout_event.cancel()
            self.ble_timeout_event = None
        if self._pairing_in_progress:
            print("[CONTROLLER] on_paired called twice — ignoring duplicate")
            return
        self._pairing_in_progress = True
        self.dm.save_pairing(credentials)
        Thread(
            target=self.do_new_pair_wifi_connect,
            args=(credentials,),
            daemon=True
        ).start()

    def do_new_pair_wifi_connect(self, credentials):
        try:
            self.new_pair_wifi_logic(credentials)
        except Exception as e:
            import traceback
            print(f"[CONTROLLER] !! New pair WiFi crash: {e}")
            traceback.print_exc()
            self._pairing_in_progress = False
            err = str(e)
            Clock.schedule_once(
                lambda dt: self.sm.get_screen('pairing').show_qr(
                    message=f"Connection error: {err}"
                ), 0
            )

    def new_pair_wifi_logic(self, credentials):
        ssid     = credentials['ssid']
        password = credentials['password']
        blemac   = credentials.get('ble_mac', '')
        name     = credentials.get('ble_name', 'your phone')

        self._wifi_cancel.clear()

        for attempt in range(1, WIFI_RETRY_LIMIT + 1):
            if self._wifi_cancel.is_set():
                print("[CONTROLLER] New pair cancelled")
                self._pairing_in_progress = False
                return

            print(f"[CONTROLLER] New pair WiFi attempt {attempt}/{WIFI_RETRY_LIMIT}")
            self.dm.network.notify_enable_hotspot()

            wait         = WIFI_FIRST_HOTSPOT_WAIT if attempt == 1 else WIFI_RETRY_INTERVAL
            retries_left = WIFI_RETRY_LIMIT - attempt

            Clock.schedule_once(
                lambda dt, a=attempt, rl=retries_left, w=wait:
                    self.sm.get_screen('pairing').show_hotspot_prompt(
                        device_name=name, attempt=a,
                        retries_left=rl, retry_in=w
                    ), 0
            )

            cancelled = self._wifi_cancel.wait(timeout=wait)
            if cancelled:
                print("[CONTROLLER] New pair cancelled during wait")
                self._pairing_in_progress = False
                return
            if self._wifi_cancel.is_set():
                self._pairing_in_progress = False
                return

            Clock.schedule_once(
                lambda dt: self.sm.get_screen('pairing').show_connecting(name), 0
            )

            wifiok = self.dm.network.connect_wifi(ssid, password)
            print(f"[CONTROLLER] WiFi result: {wifiok}")

            if wifiok:
                self._connection_time      = time.time()
                self.current_connected_mac = blemac
                self._wifi_connected       = True
                self._current_ssid         = ssid
                self.dm.update_last_connected(blemac)

                pi_ip = self.dm.network.get_local_ip()
                if pi_ip:
                    wifi_posted = self.dm.network.post_ip_via_wifi(pi_ip)
                    self.dm.network.send_ip_to_phone(pi_ip)
                    time.sleep(3 if wifi_posted else 8)
                else:
                    print("[CONTROLLER] !! Unexpected: no IP after connect()")
                    time.sleep(3)

                self.dm.network.stop_ble()
                self.dm.start_heartbeat_after_wifi(
                    on_disconnected=self.on_phone_disconnected
                )
                self._pairing_in_progress = False
                print("[CONTROLLER] New pair complete → Home")
                Clock.schedule_once(lambda dt: self.go_to_home(), 0)
                return

        self._pairing_in_progress = False
        Clock.schedule_once(
            lambda dt: self.sm.get_screen('pairing').show_qr(
                message="Please enable your phone's hotspot, scan again"
            ), 0
        )

    def on_ble_pairing_timeout(self):
        self.dm.network.stop_ble()
        self.sm.get_screen('pairing').show_qr(message="Pairing timed out - try again")

    def stop_ble_pairing(self):
        self.dm.network.stop_ble()
        self.sm.get_screen('pairing').show_qr()

    # ── Device management ─────────────────────────────────────────────────────

    def reset_pairing(self):
        self.cancel_wifi_connect()
        self.dm.reset_pairing()
        self.current_connected_mac = None
        self._wifi_connected       = False
        self._current_ssid         = None
        self._connection_time      = 0.0
        self.sm.get_screen('pairing').show_qr()
        Clock.schedule_once(
            lambda dt: self.sm.get_screen('pairing').show_qr(), 0.1
        )
        print("[CONTROLLER] All pairing data cleared")

    def forget_device(self):
        if self._wifi_connected and (time.time() - self._connection_time) < 5.0:
            print("[CONTROLLER] forget_device within 5s of connect — ghost touch, ignoring")
            return

        if self.current_connected_mac:
            known = self.dm.get_known_devices()
            match = next(
                (d for d in known if d['ble_mac'] == self.current_connected_mac), None
            )
            name = match['ble_name'] if match else self.current_connected_mac
            self.dm.remove_device(self.current_connected_mac)
            if self.dm.heartbeat:
                self.dm.heartbeat.stop()
                self.dm.heartbeat = None
            self.dm.network.stop()
            self.current_connected_mac = None
            self._wifi_connected       = False
            self._current_ssid         = None
            self._connection_time      = 0.0
            print(f"[CONTROLLER] Forgot device: {name}")
        else:
            print("[CONTROLLER] forget_device: no active device to forget")

        self.sm.current = 'pairing'
        Clock.schedule_once(lambda dt: self.start_pairing_screen(), 0.3)

    def on_phone_disconnected(self):
        if self._current_ssid and self.dm.network.is_connected_to(self._current_ssid):
            print(
                "[CONTROLLER] Heartbeat ping failed but WiFi still active — "
                "suppressing reset (phone port 8080 not running)"
            )
            return

        name = 'phone'
        if self.current_connected_mac:
            known = self.dm.get_known_devices()
            match = next(
                (d for d in known if d['ble_mac'] == self.current_connected_mac), None
            )
            if match:
                name = match['ble_name']

        print(f"[CONTROLLER] Phone disconnected ({name}) — returning to pairing")
        self.dm.network.stop()
        self.current_connected_mac = None
        self._wifi_connected       = False
        self._current_ssid         = None
        self._connection_time      = 0.0
        self.sm.current            = 'pairing'
        Clock.schedule_once(lambda dt: self.start_pairing_screen(), 0.3)

    # ── Test / sensor flow ────────────────────────────────────────────────────

    def start_test(self):
        if not self.dm.hardware.are_voc_sensors_ready():
            screen = self.sm.get_screen('home')
            screen.show_waiting_message()
            self.dm.hardware.start_voc_priming()
            self.priming_check_event = Clock.schedule_interval(self.check_voc_ready, 2.0)
        else:
            self.sm.current = 'capture'
            self.sm.get_screen('capture').start_preview()

    def check_voc_ready(self, dt):
        if self.dm.hardware.are_voc_sensors_ready():
            if self.priming_check_event:
                self.priming_check_event.cancel()
            self.sm.get_screen('home').hide_waiting_message()
            self.sm.current = 'capture'
            self.sm.get_screen('capture').start_preview()

    def capture_image(self):
        self.sm.get_screen('capture').disable_capture()
        Thread(target=self.do_capture, daemon=True).start()

    def do_capture(self):
        try:
            self.capture_logic()
        except Exception as e:
            import traceback
            print(f"[CONTROLLER] !! Capture thread crash: {e}")
            traceback.print_exc()
            err    = str(e)
            screen = self.sm.get_screen('capture')
            Clock.schedule_once(lambda dt: screen.show_error(f"Capture error: {err}"), 0)
            Clock.schedule_once(lambda dt: screen.enable_capture(), 0)

    def capture_logic(self):
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
            self.dm.pause_heartbeat()
            success = self.dm.network.send_image_to_phone(image_path)
            if success:
                self._cnn_cancel.clear()
                Clock.schedule_once(
                    lambda dt: setattr(self.sm, 'current', 'analyzing'), 0
                )
                self._cnn_timeout_event = Clock.schedule_once(
                    lambda dt: self._show_cnn_cancel_btn(), 35
                )
                Thread(target=self.wait_for_cnn_result, daemon=True).start()
            else:
                self.dm.resume_heartbeat()
                Clock.schedule_once(
                    lambda dt: screen.show_error("Failed to send image"), 0
                )
                Clock.schedule_once(lambda dt: screen.enable_capture(), 0)
        else:
            print("[CONTROLLER] Mock — skipping CNN, using default sensors")
            self.current_test_data['food_type']       = 'Unknown'
            self.current_test_data['sensors_to_read'] = ['MQ2', 'MQ3', 'MQ135']
            self.delete_image(image_path)
            Clock.schedule_once(lambda dt: self.proceed_to_reading(), 0)

    def _show_cnn_cancel_btn(self):
        if self.sm.current == 'analyzing':
            self.sm.get_screen('analyzing').show_cancel_btn()

    def cancel_analysis(self):
        self._cnn_cancel.set()
        if self._cnn_timeout_event:
            self._cnn_timeout_event.cancel()
            self._cnn_timeout_event = None
        self.dm.resume_heartbeat()
        image_path = self.current_test_data.get('image_path')
        if image_path:
            self.delete_image(image_path)
        self.current_test_data = {}
        print("[CONTROLLER] CNN analysis cancelled by user")
        Clock.schedule_once(lambda dt: self.go_to_home(), 0)

    def wait_for_cnn_result(self):
        try:
            result = self.dm.network.wait_for_cnn_result(
                cancel_event=self._cnn_cancel
            )
            if self._cnn_cancel.is_set():
                return
            if result:
                Clock.schedule_once(
                    lambda dt: self.on_cnn_result_received(result), 0
                )
            else:
                Clock.schedule_once(lambda dt: self._on_cnn_timeout(), 0)
        except Exception as e:
            print(f"[CONTROLLER] !! CNN result thread crash: {e}")
            Clock.schedule_once(lambda dt: self._on_cnn_timeout(), 0)

    def _on_cnn_timeout(self):
        if self._cnn_timeout_event:
            self._cnn_timeout_event.cancel()
            self._cnn_timeout_event = None
        self.dm.resume_heartbeat()
        image_path = self.current_test_data.get('image_path')
        if image_path:
            self.delete_image(image_path)
        self.current_test_data = {}
        self.sm.get_screen('analyzing').show_timeout_message(
            on_home=lambda: self.go_to_home()
        )

    def on_cnn_result_received(self, result):
        if self._cnn_timeout_event:
            self._cnn_timeout_event.cancel()
            self._cnn_timeout_event = None
        self.dm.resume_heartbeat()

        food_type       = result.get('food_type', '').strip().lower()
        no_match_values = {'no_match', 'no match', 'unknown', 'none', '', 'not food'}

        if food_type in no_match_values:
            print(f"[CONTROLLER] CNN returned no-match: {result}")
            image_path = self.current_test_data.get('image_path')
            if image_path:
                self.delete_image(image_path)
            self.current_test_data = {}
            self.sm.current = 'result'
            self.sm.get_screen('result').display_no_match(
                on_home=lambda: Clock.schedule_once(
                    lambda dt: self.go_to_home(), 4
                )
            )
            return

        self.current_test_data['food_type']       = result.get('food_type')
        self.current_test_data['sensors_to_read'] = result.get('sensors')
        image_path = self.current_test_data.get('image_path')
        if image_path:
            self.delete_image(image_path)
        self.proceed_to_reading()

    def proceed_to_reading(self):
        self.sm.current = 'reading'
        screen = self.sm.get_screen('reading')
        screen.set_sensors(self.current_test_data['sensors_to_read'])
        screen.start_warmup_display(                    # ← updated
            lambda: self.dm.hardware.warmup_remaining(),
            total_secs=30
        )
        Thread(target=self.read_voc_sensors, daemon=True).start()

    def read_voc_sensors(self):
        try:
            self.sensor_read_logic()
        except Exception as e:
            import traceback
            print(f"[CONTROLLER] !! Sensor read thread crash: {e}")
            traceback.print_exc()

    def sensor_read_logic(self):
        sensors     = self.current_test_data.get('sensors_to_read', [])
        reading_scr = self.sm.get_screen('reading')

        def _progress(i, total):                        # ← updated
            Clock.schedule_once(
                lambda dt: reading_scr.update_sample_progress(i, total), 0
            )

        all_data = self.dm.hardware.read_all_sensor_data(sensors, progress_cb=_progress)
        csv_path = self.dm.hardware.generate_sensor_csv(all_data)

        import config
        if config.USE_REAL_NETWORK:
            success = self.dm.network.send_csv_to_phone(csv_path)
            if success:
                result = self.dm.network.wait_for_ml_result()
                if result:
                    Clock.schedule_once(lambda dt: self.show_result(result), 0)
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
            Clock.schedule_once(lambda dt: self.show_result(mock_result), 0)

    def show_result(self, result):
        self.sm.current = 'result'
        self.sm.get_screen('result').display_result(result)

    def test_again(self):
        self.current_test_data = {}
        self.sm.current        = 'home'

    def shutdown_device(self):
        self.dm.shutdown()

    def delete_image(self, image_path):
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
                print(f"[CONTROLLER] Image deleted: {os.path.basename(image_path)}")
        except Exception as e:
            print(f"[CONTROLLER] Could not delete image: {e}")
