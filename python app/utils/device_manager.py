import os
import json
import uuid
import subprocess
import time
import config


class DeviceManager:

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

        from utils.cleanup_manager import CleanupManager
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.cleanup_manager = CleanupManager(base_dir)
        self.cleanup_manager.start()

    # ── Device ID ──────────────────────────────────────

    def get_device_id(self):
        return self.device_id

    def _load_or_generate_device_id(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    if 'device_id' in data:
                        return data['device_id']
            except Exception:
                pass
        device_id = f"MINIK-{uuid.uuid4().hex[:8].upper()}"
        self._write_config({'device_id': device_id, 'known_devices': []})
        return device_id

    def _load_config(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {'device_id': self.device_id, 'known_devices': []}

    def _write_config(self, data):
        os.makedirs(
            os.path.dirname(os.path.abspath(self.CONFIG_FILE)),
            exist_ok=True
        )
        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    # ── Known Devices ──────────────────────────────────

    def get_known_devices(self):
        return self.config_data.get('known_devices', [])

    def has_known_devices(self):
        return len(self.get_known_devices()) > 0

    def save_pairing(self, credentials):
        """Add or update device in known_devices list"""
        from datetime import datetime

        known   = self.get_known_devices()
        ble_mac = credentials.get('ble_mac', '')

        entry = {
            'ble_name':       credentials.get('ble_name', ''),
            'ble_mac':        ble_mac,
            'ssid':           credentials.get('ssid', ''),
            'phone_address':  credentials.get('phone_address', ''),
            'last_connected': datetime.now().isoformat()
        }

        existing = next(
            (d for d in known if d.get('ble_mac') == ble_mac), None
        )

        if existing:
            known[known.index(existing)] = entry
            print(f"[DEVICE] Updated known device: {entry['ble_name']}")
        else:
            known.append(entry)
            print(f"[DEVICE] New device saved: {entry['ble_name']}")

        self.config_data['known_devices'] = known
        self._write_config(self.config_data)

        if config.USE_REAL_NETWORK and credentials.get('phone_address'):
            self._start_heartbeat(credentials['phone_address'])

    def update_last_connected(self, ble_mac):
        """Update timestamp on successful reconnect"""
        from datetime import datetime
        known = self.get_known_devices()
        for device in known:
            if device.get('ble_mac') == ble_mac:
                device['last_connected'] = datetime.now().isoformat()
                break
        self.config_data['known_devices'] = known
        self._write_config(self.config_data)

    def reset_pairing(self):
        """Clear all known devices, keep device ID"""
        if self.heartbeat:
            self.heartbeat.stop()
            self.heartbeat = None
        self.config_data['known_devices'] = []
        self._write_config(self.config_data)
        print("[DEVICE] All pairing data cleared")

    def remove_device(self, ble_mac):
        """Remove a single device by BLE MAC"""
        known = [
            d for d in self.get_known_devices()
            if d.get('ble_mac') != ble_mac
        ]
        self.config_data['known_devices'] = known
        self._write_config(self.config_data)
        print(f"[DEVICE] Removed device: {ble_mac}")

    # ── Boot Scan ──────────────────────────────────────

    def scan_for_known_devices(self, timeout=10):
       """
       Scan BLE for any previously paired device.
       Returns full known_device dict if found, else None.
       Works identically in both mock and real mode.
       """
       known = self.get_known_devices()
       if not known:
           print("[DEVICE] No known devices to scan for")
           return None

       known_macs  = {d['ble_mac']: d for d in known}
       known_names = {d['ble_name']: d for d in known}

       print(f"[DEVICE] Scanning for {len(known)} known device(s)... "
             f"({'mock' if not config.USE_REAL_NETWORK else 'real'})")

       found = self.network.scan_for_devices(
           known_macs=list(known_macs.keys()),
           known_names=list(known_names.keys()),
           timeout=timeout
        )

       if found:
           # Look up the full known_device entry by MAC or name
           mac   = found.get('mac', '')
           name  = found.get('name', '')
           match = known_macs.get(mac) or known_names.get(name)
           if match:
               print(f"[DEVICE] Found known device: {match['ble_name']}")
               return match

       print("[DEVICE] No known devices found nearby")
       return None


    # ── Heartbeat ──────────────────────────────────────

    def _start_heartbeat(self, phone_address):
        from network.heartbeat_manager import HeartbeatManager
        if self.heartbeat:
            self.heartbeat.stop()
        self.heartbeat = HeartbeatManager(
            phone_address=phone_address,
            on_connected=lambda: print("[DEVICE] Phone app ONLINE"),
            on_disconnected=lambda: print("[DEVICE] Phone app OFFLINE")
        )
        self.heartbeat.start()

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
        if config.USE_REAL_CAMERA:
            try:
                from hardware.camera_manager import CameraManager
                self.camera = CameraManager()
                print("[HARDWARE] Using REAL camera")
            except ImportError as e:
                print(f"[HARDWARE] Camera fallback to MOCK: {e}")
                from hardware.mock_hardware import MockCameraManager
                self.camera = MockCameraManager()
        else:
            from hardware.mock_hardware import MockCameraManager
            self.camera = MockCameraManager()
            print("[HARDWARE] Using MOCK camera")

        if config.USE_REAL_SENSORS or config.USE_REAL_DHT11:
            try:
                from hardware.sensor_manager import SensorManager
                self.sensors = SensorManager()
                print("[HARDWARE] Using REAL sensors")
            except ImportError as e:
                print(f"[HARDWARE] Sensors fallback to MOCK: {e}")
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
        self.mode      = 'ble'

        if config.USE_REAL_NETWORK:
            try:
                from network.ble_manager  import BLEManager
                from network.wifi_manager import WiFiManager
                self.ble  = BLEManager(device_id)
                self.wifi = WiFiManager()
                print("[NETWORK] Using REAL BLE/WiFi")
            except ImportError as e:
                print(f"[NETWORK] Fallback to MOCK: {e}")
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

    def scan_for_devices(self, known_macs, known_names, timeout=10):
        if hasattr(self.ble, 'scan_for_devices'):
            return self.ble.scan_for_devices(known_macs, known_names, timeout)
        return None

    def wait_for_pairing(self):         return self.ble.wait_for_pairing()
    def stop_ble(self):                 return self.ble.stop()

    def connect_wifi(self, ssid, password=None):
        ok = self.wifi.connect(ssid, password)
        if ok:
            self.mode = 'wifi'
        return ok

    def get_local_ip(self):
        if hasattr(self.wifi, 'get_local_ip'):
            return self.wifi.get_local_ip()
        return None

    def send_ip_to_phone(self, ip):
        if hasattr(self.ble, 'send_ip_to_phone'):
            return self.ble.send_ip_to_phone(ip)
        return False

    def notify_enable_hotspot(self):
        """Tell phone via BLE that its hotspot needs to be turned on"""
        if hasattr(self.ble, 'notify_enable_hotspot'):
            return self.ble.notify_enable_hotspot()
        if hasattr(self.wifi, 'notify_enable_hotspot'):
            return self.wifi.notify_enable_hotspot()
        return False

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
