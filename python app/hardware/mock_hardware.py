import time
import random
import config


class MockNetworkManager:
    """
    Simulates all BLE/WiFi states.
    BLE (device nearby) and hotspot (WiFi available) are independent.
    Use config.MOCK_HOTSPOT_ON to test both paths.
    """

    def __init__(self, device_id):
        self.device_id = device_id
        self.mode      = 'ble'

    # ── BLE ─────────────────────────────────────────────

    def start_advertising(self):
        return self.start_ble_advertising()

    def start_ble_advertising(self):
        print(f"[MOCK BLE] Advertising as MiniK-{self.device_id[-6:]}")
        return True

    def scan_for_devices(self, known_macs, known_names, timeout=10):
        """
        Simulate BLE scan. Always returns a device if known list is non-empty.
        BLE = phone is nearby. Hotspot state checked separately during WiFi connect.
        """
        print(f"[MOCK BLE] Scanning ({timeout}s) for "
              f"{len(known_macs)} known device(s)...")
        time.sleep(min(2, timeout))  # Simulate scan time

        if known_macs:
            found = {
                'mac':  known_macs[0],
                'name': known_names[0] if known_names else 'MockPhone'
            }
            print(f"[MOCK BLE] Found: {found['name']} ({found['mac']})")
            return found

        print("[MOCK BLE] No known devices found")
        return None

    def wait_for_pairing(self):
        """Simulate phone scanning QR and sending credentials"""
        print("[MOCK BLE] Waiting for phone to send credentials...")
        time.sleep(3)
        credentials = {
            'ble_name':      'MockPhone-AB12',
            'ble_mac':       'AA:BB:CC:DD:EE:FF',
            'ssid':          'MockHotspot',
            'password':      'mockpass123',
            'phone_address': '192.168.43.1'
        }
        print(f"[MOCK BLE] Credentials received: SSID={credentials['ssid']}")
        return credentials

    def send_ip_to_phone(self, ip_address):
        print(f"[MOCK BLE] IP sent to phone: {ip_address}")
        return True

    def notify_enable_hotspot(self):
        """
        In real mode: writes to BLE STATUS characteristic → phone shows notification.
        Mock: just logs it.
        """
        print("[MOCK BLE] ← Notified phone: please enable your hotspot")
        return True

    def stop(self):
        print("[MOCK BLE] Advertising stopped")

    # ── WiFi / Hotspot ───────────────────────────────────

    def connect(self, ssid, password=None):
        """
        Simulate hotspot connect.
        Respects config.MOCK_HOTSPOT_ON:
            True  → success  (hotspot is on)
            False → failure  (hotspot is off - triggers retry/prompt)
        """
        print(f"[MOCK WIFI] Connecting to hotspot: '{ssid}'...")
        time.sleep(1.5)  # Simulate nmcli delay

        if config.MOCK_HOTSPOT_ON:
            self.mode = 'wifi'
            print(f"[MOCK WIFI] Connected to '{ssid}' ✓")
            return True
        else:
            print(f"[MOCK WIFI] Hotspot '{ssid}' not available "
                  f"(MOCK_HOTSPOT_ON=False)")
            return False

    def get_local_ip(self):
        print("[MOCK WIFI] Local IP: 192.168.43.100")
        return '192.168.43.100'

    def start_server(self):
        print("[MOCK WIFI] Flask server started on :8765")

    def send_image(self, image_path):
        print(f"[MOCK WIFI] Sending image: {image_path}")
        time.sleep(0.5)
        print("[MOCK WIFI] Image sent ✓")
        return True

    def send_file(self, file_path):
        print(f"[MOCK WIFI] Sending CSV: {file_path}")
        time.sleep(0.3)
        print("[MOCK WIFI] CSV sent ✓")
        return True

    def wait_for_message(self, message_type):
        print(f"[MOCK WIFI] Waiting for {message_type}...")
        time.sleep(2)

        if message_type == 'cnn_result':
            return {
                'food_type':  random.choice(['Fish', 'Chicken', 'Beef', 'Pork']),
                'sensors':    ['MQ2', 'MQ3', 'MQ135'],
                'confidence': round(random.uniform(80, 99), 1)
            }
        if message_type == 'ml_result':
            return {
                'status':     random.choice(['Fresh', 'Moderate', 'Spoiled']),
                'confidence': round(random.uniform(75, 99), 1),
                'food_type':  'Unknown',
                'details':    'Mock ML result'
            }
        return None


class MockCameraManager:

    def initialize(self):
        print("[MOCK CAM] Initialized")

    def start_preview(self):
        print("[MOCK CAM] Preview started")

    def stop_preview(self):
        print("[MOCK CAM] Preview stopped")

    def get_preview_texture(self):
        return None

    def capture_image(self):
        import os
        from datetime import datetime
        base_dir     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        captures_dir = os.path.join(base_dir, 'captures')
        os.makedirs(captures_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(captures_dir, f"mock_capture_{timestamp}.jpg")
        # Create empty placeholder file
        open(path, 'w').close()
        print(f"[MOCK CAM] Captured: {path}")
        return path

    def cleanup(self):
        print("[MOCK CAM] Cleanup")


class MockSensorManager:

    def initialize(self):
        print("[MOCK SENSORS] Initialized")

    def start_priming(self):
        print("[MOCK SENSORS] Priming started")

    def are_ready(self):
        return True

    def read_all_data(self, sensor_list):
        data = {
            'temperature': round(random.uniform(20, 35), 1),
            'humidity':    round(random.uniform(40, 80), 1),
            'sensors':     {}
        }
        for sensor in sensor_list:
            data['sensors'][sensor] = round(random.uniform(100, 900), 2)
        print(f"[MOCK SENSORS] Data: {data}")
        return data

    def generate_csv(self, data):
        import os
        from datetime import datetime
        base_dir  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir  = os.path.join(base_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(data_dir, f"sensors_{timestamp}.csv")
        with open(path, 'w') as f:
            f.write("timestamp,temperature,humidity")
            for s in data.get('sensors', {}):
                f.write(f",{s}")
            f.write("\n")
            f.write(f"{timestamp},{data['temperature']},{data['humidity']}")
            for v in data.get('sensors', {}).values():
                f.write(f",{v}")
            f.write("\n")
        print(f"[MOCK SENSORS] CSV: {path}")
        return path

    def cleanup(self):
        print("[MOCK SENSORS] Cleanup")
