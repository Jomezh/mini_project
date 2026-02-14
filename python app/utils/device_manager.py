import os
import json
import uuid
import config  # Import config module


class DeviceManager:
    """Central device management class"""
    
    CONFIG_FILE = '/home/pi/.minik_config.json' if config.IS_RASPBERRY_PI else './minik_config.json'
    
    def __init__(self):
        self.device_id = self._load_or_generate_device_id()
        self.config_data = self._load_config()
        
        # Initialize hardware (respects config flags)
        self.hardware = HardwareManager()
        
        # Initialize network (respects config flags)
        self.network = NetworkManager(self.device_id)
    
    def _load_or_generate_device_id(self):
        """Load existing device ID or generate new one"""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    config_data = json.load(f)
                    return config_data.get('device_id')
            except:
                pass
        
        # Generate new device ID
        device_id = f"MINIK-{uuid.uuid4().hex[:8].upper()}"
        self._save_device_id(device_id)
        return device_id
    
    def _save_device_id(self, device_id):
        """Save device ID to config file"""
        config_data = {'device_id': device_id}
        os.makedirs(os.path.dirname(self.CONFIG_FILE), exist_ok=True)
        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(config_data, f)
    
    def _load_config(self):
        """Load device configuration"""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def get_device_id(self):
        return self.device_id
    
    def is_paired(self):
        """Check if device is already paired"""
        return 'paired' in self.config_data and self.config_data['paired']
    
    def save_pairing(self, credentials):
        """Save pairing information"""
        self.config_data['paired'] = True
        self.config_data['ssid'] = credentials['ssid']
        self.config_data['phone_address'] = credentials.get('phone_address')
        
        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(self.config_data, f)
    
    def cleanup(self):
        """Cleanup resources"""
        self.hardware.cleanup()
        self.network.cleanup()
    
    def shutdown(self):
        """Shutdown the device"""
        self.cleanup()
        if config.IS_RASPBERRY_PI:
            os.system('sudo shutdown -h now')
        else:
            print("[MOCK] Shutdown requested (desktop mode)")
            from kivy.app import App
            App.get_running_app().stop()


class HardwareManager:
    """Manages all hardware components with config-based switching"""
    
    def __init__(self):
        # Camera selection
        if config.USE_REAL_CAMERA:
            try:
                from hardware.camera_manager import CameraManager
                self.camera = CameraManager()
                print("[HARDWARE] Using REAL camera")
            except ImportError as e:
                print(f"[HARDWARE] Real camera import failed: {e}")
                print("[HARDWARE] Falling back to MOCK camera")
                from hardware.mock_hardware import MockCameraManager
                self.camera = MockCameraManager()
        else:
            from hardware.mock_hardware import MockCameraManager
            self.camera = MockCameraManager()
            print("[HARDWARE] Using MOCK camera")
        
        # Sensor selection (includes DHT11)
        if config.USE_REAL_SENSORS or config.USE_REAL_DHT11:
            try:
                from hardware.sensor_manager import SensorManager
                self.sensors = SensorManager()
                print("[HARDWARE] Using REAL sensors")
            except ImportError as e:
                print(f"[HARDWARE] Real sensor import failed: {e}")
                print("[HARDWARE] Falling back to MOCK sensors")
                from hardware.mock_hardware import MockSensorManager
                self.sensors = MockSensorManager()
        else:
            from hardware.mock_hardware import MockSensorManager
            self.sensors = MockSensorManager()
            print("[HARDWARE] Using MOCK sensors")
    
    def initialize(self):
        """Initialize hardware"""
        self.sensors.initialize()
        self.camera.initialize()
    
    def start_voc_priming(self):
        self.sensors.start_priming()
    
    def are_voc_sensors_ready(self):
        return self.sensors.are_ready()
    
    def read_voc_sensors(self, sensor_list):
        return self.sensors.read_sensors(sensor_list)
    
    def read_environment(self):
        """Read temperature and humidity"""
        return self.sensors.read_environment()
    
    def read_all_sensor_data(self, sensor_list):
        """Read VOC sensors + environmental data together"""
        return self.sensors.read_all_data(sensor_list)
    
    def generate_sensor_csv(self, sensor_data):
        return self.sensors.generate_csv(sensor_data)
    
    def start_camera_preview(self):
        self.camera.start_preview()
    
    def stop_camera_preview(self):
        self.camera.stop_preview()
    
    def get_preview_texture(self):
        return self.camera.get_preview_texture()
    
    def capture_image(self):
        return self.camera.capture_image()
    
    def cleanup(self):
        self.sensors.cleanup()
        self.camera.cleanup()


class NetworkManager:
    """Manages network communications with config-based switching"""
    
    def __init__(self, device_id):
        self.device_id = device_id
        
        if config.USE_REAL_NETWORK:
            try:
                from network.ble_manager import BLEManager
                from network.wifi_manager import WiFiManager
                self.ble = BLEManager(device_id)
                self.wifi = WiFiManager()
                print("[NETWORK] Using REAL BLE/WiFi")
            except ImportError as e:
                print(f"[NETWORK] Real network import failed: {e}")
                print("[NETWORK] Falling back to MOCK network")
                from hardware.mock_hardware import MockNetworkManager
                mock = MockNetworkManager(device_id)
                self.ble = mock
                self.wifi = mock
        else:
            from hardware.mock_hardware import MockNetworkManager
            mock = MockNetworkManager(device_id)
            self.ble = mock
            self.wifi = mock
            print("[NETWORK] Using MOCK network")
        
        self.mode = 'ble'
    
    def start_ble_advertising(self):
        return self.ble.start_advertising() if hasattr(self.ble, 'start_advertising') else self.ble.start_ble_advertising()
    
    def wait_for_pairing(self):
        return self.ble.wait_for_pairing()
    
    def stop_ble(self):
        return self.ble.stop()
    
    def connect_wifi(self, ssid, password):
        success = self.wifi.connect(ssid, password)
        if success:
            self.mode = 'wifi'
        return success
    
    def start_wifi_server(self):
        if hasattr(self.wifi, 'start_server'):
            self.wifi.start_server()
    
    def send_image_to_phone(self, image_path):
        if self.mode == 'wifi':
            return self.wifi.send_image(image_path)
        return False
    
    def wait_for_cnn_result(self):
        if self.mode == 'wifi':
            return self.wifi.wait_for_message('cnn_result')
        return None
    
    def send_csv_to_phone(self, csv_path):
        if self.mode == 'wifi':
            return self.wifi.send_file(csv_path)
        return False
    
    def wait_for_ml_result(self):
        if self.mode == 'wifi':
            return self.wifi.wait_for_message('ml_result')
        return None
    
    def cleanup(self):
        if hasattr(self.ble, 'stop'):
            self.ble.stop()
        if hasattr(self.wifi, 'stop'):
            self.wifi.stop()
