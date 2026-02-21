import os
import json
import uuid
import subprocess
import config


class DeviceManager:
    """Central device management"""

    CONFIG_FILE = (
        '/home/minik/.minik_config.json'
        if config.IS_RASPBERRY_PI
        else './minik_config.json'
    )

    def __init__(self):
        self.device_id   = self._load_or_generate_device_id()
        self.config_data = self._load_config()
        self.hardware    = HardwareManager()
        self.network     = NetworkManager(self.device_id)
        self.heartbeat   = None

        # Start automatic storage cleanup
        from utils.cleanup_manager import CleanupManager
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.cleanup_manager = CleanupManager(base_dir)
        self.cleanup_manager.start()

    # ── Device ID ──────────────────────────────────────

    def _load_or_generate_device_id(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    return json.load(f).get('device_id')
            except Exception:
                pass
        device_id = f"MINIK-{uuid.uuid4().hex[:8].upper()}"
        self._write_config({'device_id': device_id})
        return device_id

    def _load_config(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _write_config(self, data):
        os.makedirs(os.path.dirname(os.path.abspath(self.CONFIG_FILE)), exist_ok=True)
        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    # ── Pairing ────────────────────────────────────────

    def get_device_id(self):
        return self.device_id

    def is_paired(self):
        return self.config_data.get('paired', False)

    def save_pairing(self, credentials):
        """Save pairing info and start heartbeat monitor"""
        self.config_data['paired']        = True
        self.config_data['ssid']          = credentials.get('ssid')
        self.config_data['phone_address'] = credentials.get('phone_address')
        self._write_config(self.config_data)
        print(f"[DEVICE] Pairing saved - SSID: {credentials.get('ssid')}")

        if config.USE_REAL_NETWORK and credentials.get('phone_address'):
            self._start_heartbeat(credentials['phone_address'])

    def reset_pairing(self):
        """Clear all pairing data from config file"""
        keys_to_remove = ['paired', 'ssid', 'phone_address']
        for key in keys_to_remove:
           self.config.pop(key, None)

        with open(self.CONFIG_FILE, 'w') as f:
           json.dump(self.config, f)

        print("[DEVICE] Pairing data cleared")


    # ── Boot Connection Verification ───────────────────

    def verify_connection_on_boot(self):
        """
        Called at boot when device was previously paired.
        Returns:
            True        - WiFi + phone both reachable
            'wifi_only' - WiFi ok but phone offline
            False       - WiFi not found (triggers re-pair)
        """
        if not config.USE_REAL_NETWORK:
            print("[DEVICE] Mock mode - skipping boot check")
            return True

        saved_ssid    = self.config_data.get('ssid')
        phone_address = self.config_data.get('phone_address')

        if not saved_ssid:
            print("[DEVICE] No saved WiFi - need to pair")
            return False

        print(f"[DEVICE] Boot check: verifying WiFi '{saved_ssid}'")

        wifi_ok = self._check_wifi_connected(saved_ssid)
        if not wifi_ok:
            print(f"[DEVICE] WiFi '{saved_ssid}' not reachable - resetting pairing")
            self.reset_pairing()
            return False

        if phone_address:
            phone_ok = self._ping_host(phone_address)
            if not phone_ok:
                print(f"[DEVICE] Phone at {phone_address} not reachable (may be offline)")
                return 'wifi_only'

        print("[DEVICE] Boot check: all connections OK")
        return True

    def _check_wifi_connected(self, expected_ssid, retries=3):
        import time
        for attempt in range(retries):
            try:
                result = subprocess.run(
                    ['iwgetid', '-r'],
                    capture_output=True, text=True, timeout=5
                )
                current = result.stdout.strip()
                if current == expected_ssid:
                    return True
                print(f"[DEVICE] WiFi attempt {attempt+1}: "
                      f"on '{current}', expected '{expected_ssid}'")
                if attempt < retries - 1:
                    time.sleep(3)
            except Exception as e:
                print(f"[DEVICE] WiFi check error: {e}")
        return False

    def _ping_host(self, host, timeout=3):
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', str(timeout), host],
                capture_output=True, timeout=timeout + 2
            )
            return result.returncode == 0
        except Exception:
            return False

    # ── Heartbeat ──────────────────────────────────────

    def _start_heartbeat(self, phone_address):
        from network.heartbeat_manager import HeartbeatManager
        self.heartbeat = HeartbeatManager(
            phone_address=phone_address,
            on_connected=self._on_phone_online,
            on_disconnected=self._on_phone_offline
        )
        self.heartbeat.start()

    def _on_phone_online(self):
        print("[DEVICE] Phone app came ONLINE")

    def _on_phone_offline(self):
        print("[DEVICE] Phone app went OFFLINE")

    # ── Cleanup / Shutdown ─────────────────────────────

    def cleanup(self):
        self.hardware.cleanup()
        self.network.cleanup()
        self.cleanup_manager.stop()
        if self.heartbeat:
            self.heartbeat.stop()

    def shutdown(self):
        self.cleanup()
        if config.IS_RASPBERRY_PI:
            os.system('sudo shutdown -h now')
        else:
            print("[MOCK] Shutdown requested")
            from kivy.app import App
            App.get_running_app().stop()


# ──────────────────────────────────────────────────────
# HardwareManager
# ──────────────────────────────────────────────────────

class HardwareManager:

    def __init__(self):
        # Camera (lazy import)
        if config.USE_REAL_CAMERA:
            try:
                from hardware.camera_manager import CameraManager
                self.camera = CameraManager()
                print("[HARDWARE] Using REAL camera")
            except ImportError as e:
                print(f"[HARDWARE] Camera import failed: {e} - falling back to MOCK")
                from hardware.mock_hardware import MockCameraManager
                self.camera = MockCameraManager()
        else:
            from hardware.mock_hardware import MockCameraManager
            self.camera = MockCameraManager()
            print("[HARDWARE] Using MOCK camera")

        # Sensors (lazy import)
        if config.USE_REAL_SENSORS or config.USE_REAL_DHT11:
            try:
                from hardware.sensor_manager import SensorManager
                self.sensors = SensorManager()
                print("[HARDWARE] Using REAL sensors")
            except ImportError as e:
                print(f"[HARDWARE] Sensor import failed: {e} - falling back to MOCK")
                from hardware.mock_hardware import MockSensorManager
                self.sensors = MockSensorManager()
        else:
            from hardware.mock_hardware import MockSensorManager
            self.sensors = MockSensorManager()
            print("[HARDWARE] Using MOCK sensors")

    def initialize(self):
        self.sensors.initialize()
        self.camera.initialize()

    def start_voc_priming(self):        self.sensors.start_priming()
    def are_voc_sensors_ready(self):    return self.sensors.are_ready()
    def read_voc_sensors(self, sl):     return self.sensors.read_sensors(sl)
    def read_environment(self):         return self.sensors.read_environment()
    def read_all_sensor_data(self, sl): return self.sensors.read_all_data(sl)
    def generate_sensor_csv(self, d):   return self.sensors.generate_csv(d)
    def start_camera_preview(self):     self.camera.start_preview()
    def stop_camera_preview(self):      self.camera.stop_preview()
    def get_preview_texture(self):      return self.camera.get_preview_texture()
    def capture_image(self):            return self.camera.capture_image()

    def cleanup(self):
        self.sensors.cleanup()
        self.camera.cleanup()


# ──────────────────────────────────────────────────────
# NetworkManager
# ──────────────────────────────────────────────────────

class NetworkManager:

    def __init__(self, device_id):
        self.device_id = device_id
        self.mode = 'ble'

        if config.USE_REAL_NETWORK:
            try:
                from network.ble_manager  import BLEManager
                from network.wifi_manager import WiFiManager
                self.ble  = BLEManager(device_id)
                self.wifi = WiFiManager()
                print("[NETWORK] Using REAL BLE/WiFi")
            except ImportError as e:
                print(f"[NETWORK] Network import failed: {e} - falling back to MOCK")
                from hardware.mock_hardware import MockNetworkManager
                mock = MockNetworkManager(device_id)
                self.ble = self.wifi = mock
        else:
            from hardware.mock_hardware import MockNetworkManager
            mock = MockNetworkManager(device_id)
            self.ble = self.wifi = mock
            print("[NETWORK] Using MOCK network")

    def start_ble_advertising(self):
        fn = getattr(self.ble, 'start_advertising',
                     getattr(self.ble, 'start_ble_advertising', None))
        return fn() if fn else False

    def wait_for_pairing(self):         return self.ble.wait_for_pairing()
    def stop_ble(self):                 return self.ble.stop()

    def connect_wifi(self, ssid, pw):
        ok = self.wifi.connect(ssid, pw)
        if ok:
            self.mode = 'wifi'
        return ok

    def start_wifi_server(self):
        if hasattr(self.wifi, 'start_server'):
            self.wifi.start_server()

    def send_image_to_phone(self, path):
        return self.wifi.send_image(path) if self.mode == 'wifi' else False

    def wait_for_cnn_result(self):
        return self.wifi.wait_for_message('cnn_result') if self.mode == 'wifi' else None

    def send_csv_to_phone(self, path):
        return self.wifi.send_file(path) if self.mode == 'wifi' else False

    def wait_for_ml_result(self):
        return self.wifi.wait_for_message('ml_result') if self.mode == 'wifi' else None

    def cleanup(self):
        if hasattr(self.ble,  'stop'): self.ble.stop()
        if hasattr(self.wifi, 'stop'): self.wifi.stop()
    def get_local_ip(self):
       """Get Pi's current IP on wlan0"""
       if hasattr(self.wifi, 'get_local_ip'):
           return self.wifi.get_local_ip()
       return None

    def send_ip_to_phone(self, ip_address):
        """Write Pi IP to BLE characteristic so phone can read it"""
        if hasattr(self.ble, 'send_ip_to_phone'):
           return self.ble.send_ip_to_phone(ip_address)
        return False
