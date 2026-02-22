import time
import random
import config


class MockNetworkManager:
    """
    Simulates all BLE/WiFi states.
    BLE (device nearby) and hotspot (WiFi available) are independent flags.

    config.MOCK_BLE_DEVICE_FOUND:
        True  → scan finds phone → proceeds to WiFi connect
        False → scan finds nothing → QR screen shown

    config.MOCK_HOTSPOT_ON:
        True  → WiFi connect succeeds
        False → hotspot off → retry prompt shown, BLE notified
    """

    def __init__(self, device_id):
        self.device_id = device_id
        self.mode      = 'ble'

    # ── BLE ─────────────────────────────────────────────

    def start_advertising(self):
        return self.start_ble_advertising()

    def start_ble_advertising(self):
        ble_name = f"MiniK-{self.device_id[-6:]}"
        print(f"[MOCK BLE] Advertising as '{ble_name}' "
              f"(overrides system hostname)")
        return True

    def scan_for_devices(self, known_macs, known_names, timeout=10):
        """
        Simulate BLE scan.
        Returns found device dict if MOCK_BLE_DEVICE_FOUND=True and list non-empty.
        Returns None if MOCK_BLE_DEVICE_FOUND=False → triggers QR screen.
        """
        print(f"[MOCK BLE] Scanning ({timeout}s) for "
              f"{len(known_macs)} known device(s)...")
        time.sleep(min(2, timeout))  # Simulate scan duration

        if known_macs and config.MOCK_BLE_DEVICE_FOUND:
            found = {
                'mac':  known_macs[0],
                'name': known_names[0] if known_names else 'MockPhone'
            }
            print(f"[MOCK BLE] Found: {found['name']} ({found['mac']})")
            return found

        if not config.MOCK_BLE_DEVICE_FOUND:
            print("[MOCK BLE] No devices found "
                  "(MOCK_BLE_DEVICE_FOUND=False → QR screen)")
        else:
            print("[MOCK BLE] No known devices in list")
        return None

    def wait_for_pairing(self):
        """
        Simulate phone scanning QR and sending credentials via BLE GATT.
        In real mode: phone writes to SSID/PASSWORD/MAC characteristics.
        ble_mac here is the PHONE's MAC - Pi saves this for future reconnect scans.
        """
        print("[MOCK BLE] Waiting for phone to connect and send credentials...")
        time.sleep(3)
        credentials = {
            'ble_name':      'MockPhone-AB12',
            'ble_mac':       'AA:BB:CC:DD:EE:FF',   # Phone's MAC (not Pi's)
            'ssid':          'MockHotspot',
            'password':      'mockpass123',
            'phone_address': '192.168.43.1'
        }
        print(f"[MOCK BLE] Credentials received from {credentials['ble_name']}: "
              f"SSID='{credentials['ssid']}'")
        return credentials

    def send_ip_to_phone(self, ip_address):
        """
        In real mode: Pi writes IP to GATT IP characteristic.
        Phone reads it → saves for WiFi comms.
        """
        print(f"[MOCK BLE] Pi IP sent to phone: {ip_address}")
        return True

    def notify_enable_hotspot(self):
        """
        In real mode: Pi writes to GATT STATUS characteristic.
        Phone app receives notification → shows "Enable hotspot" alert.
        Mock: just logs it.
        """
        print("[MOCK BLE] ← Notified phone via BLE: please enable your hotspot")
        return True

    def stop(self):
        print("[MOCK BLE] BLE advertising/connection stopped")

    # ── WiFi / Hotspot ───────────────────────────────────

    def connect(self, ssid, password=None):
        """
        Simulate hotspot connect via nmcli.
        password=None → nmcli uses saved credentials (reconnect flow).
        password=str  → new credentials (fresh pair flow).
        Respects config.MOCK_HOTSPOT_ON.
        """
        if password:
            print(f"[MOCK WIFI] Connecting to hotspot: '{ssid}' "
                  f"(new credentials)...")
        else:
            print(f"[MOCK WIFI] Connecting to hotspot: '{ssid}' "
                  f"(saved credentials)...")
        time.sleep(1.5)  # Simulate nmcli delay

        if config.MOCK_HOTSPOT_ON:
            self.mode = 'wifi'
            print(f"[MOCK WIFI] Connected to '{ssid}' ✓")
            return True
        else:
            print(f"[MOCK WIFI] Hotspot '{ssid}' not reachable "
                  f"(MOCK_HOTSPOT_ON=False)")
            return False

    def get_local_ip(self):
        ip = '192.168.43.100'
        print(f"[MOCK WIFI] Local IP: {ip}")
        return ip

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
        print(f"[MOCK WIFI] Waiting for {message_type} from phone...")
        time.sleep(2)

        if message_type == 'cnn_result':
            result = {
                'food_type':  random.choice(['Fish', 'Chicken', 'Beef', 'Pork']),
                'sensors':    ['MQ2', 'MQ3', 'MQ135'],
                'confidence': round(random.uniform(80, 99), 1)
            }
            print(f"[MOCK WIFI] CNN result: {result['food_type']} "
                  f"({result['confidence']}%)")
            return result

        if message_type == 'ml_result':
            result = {
                'status':     random.choice(['Fresh', 'Moderate', 'Spoiled']),
                'confidence': round(random.uniform(75, 99), 1),
                'food_type':  'Unknown',
                'details':    'Mock ML result'
            }
            print(f"[MOCK WIFI] ML result: {result['status']} "
                  f"({result['confidence']}%)")
            return result

        return None


class MockCameraManager:

    def initialize(self):
        print("[MOCK CAM] Initialized")

    def start_preview(self):
        print("[MOCK CAM] Preview started")

    def stop_preview(self):
        print("[MOCK CAM] Preview stopped")

    def get_preview_texture(self):
        # Returns None - capture screen handles this gracefully
        return None

    def capture_image(self):
        import os
        from datetime import datetime
        base_dir     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        captures_dir = os.path.join(base_dir, 'captures')
        os.makedirs(captures_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(captures_dir, f"mock_capture_{timestamp}.jpg")
        open(path, 'w').close()   # Empty placeholder file
        print(f"[MOCK CAM] Captured: {path}")
        return path

    def cleanup(self):
        print("[MOCK CAM] Cleanup")


class MockSensorManager:

    def initialize(self):
        print("[MOCK SENSORS] Initialized")

    def start_priming(self):
        print("[MOCK SENSORS] Priming started (mock - instant ready)")

    def are_ready(self):
        return True  # Mock sensors always ready instantly

    def read_all_data(self, sensor_list):
        data = {
            'temperature': round(random.uniform(20, 35), 1),
            'humidity':    round(random.uniform(40, 80), 1),
            'sensors':     {}
        }
        for sensor in sensor_list:
            data['sensors'][sensor] = round(random.uniform(100, 900), 2)
        print(f"[MOCK SENSORS] Read: temp={data['temperature']}°C  "
              f"hum={data['humidity']}%  "
              f"VOC={data['sensors']}")
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
        print(f"[MOCK SENSORS] CSV saved: {path}")
        return path

    def cleanup(self):
        print("[MOCK SENSORS] Cleanup")
