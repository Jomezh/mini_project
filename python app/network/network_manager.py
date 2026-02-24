"""
Unified facade combining BLEManager + WiFiManager.
This is what app_controller.py talks to via dm.network.
Method names here must match app_controller.py exactly.
"""

from network.ble_manager  import BLEManager
from network.wifi_manager import WiFiManager


class NetworkManager:

    def __init__(self, device_id):
        self._ble  = BLEManager(device_id)
        self._wifi = WiFiManager()

    # ── BLE ──────────────────────────────────────────────

    def start_ble_advertising(self):
        return self._ble.start_advertising()

    def scan_for_devices(self, known_macs, known_names, timeout=10):
        return self._ble.scan_for_devices(known_macs, known_names, timeout)

    def wait_for_pairing(self):
        return self._ble.wait_for_pairing()

    def send_ip_to_phone(self, ip_address):
        return self._ble.send_ip_to_phone(ip_address)

    def notify_enable_hotspot(self):
        return self._ble.notify_enable_hotspot()

    def stop_ble(self):
        return self._ble.stop()

    # ── WiFi ─────────────────────────────────────────────

    def connect_wifi(self, ssid, password=None):
        return self._wifi.connect(ssid, password)

    def get_local_ip(self):
        return self._wifi.get_local_ip()

    def start_wifi_server(self):
        return self._wifi.start_server()

    def send_image_to_phone(self, image_path):
        return self._wifi.send_image(image_path)

    def send_csv_to_phone(self, file_path):
        return self._wifi.send_file(file_path)

    def wait_for_cnn_result(self, timeout=120):
        return self._wifi.wait_for_message('cnn_result', timeout)

    def wait_for_ml_result(self, timeout=120):
        return self._wifi.wait_for_message('ml_result', timeout)

    def stop(self):
        self.stop_ble()
        self._wifi.stop()
