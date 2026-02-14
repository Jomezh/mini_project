import os
import json
import uuid
from hardware.sensor_manager import SensorManager
from hardware.camera_manager import CameraManager
from network.ble_manager import BLEManager
from network.wifi_manager import WiFiManager
from hardware.display_manager import DisplayManager


class DeviceManager:
    """Central device management class"""
    
    CONFIG_FILE = '/home/pi/.minik_config.json'
    
    def __init__(self):
        self.device_id = self._load_or_generate_device_id()
        self.config = self._load_config()
        
        # Initialize hardware
        self.hardware = HardwareManager()
        
        # Initialize network
        self.network = NetworkManager(self.device_id)
    
    def _load_or_generate_device_id(self):
        """Load existing device ID or generate new one"""
        if os.path.exists(self.CONFIG_FILE):
            with open(self.CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get('device_id')
        
        # Generate new device ID
        device_id = f"MINIK-{uuid.uuid4().hex[:8].upper()}"
        self._save_device_id(device_id)
        return device_id
    
    def _save_device_id(self, device_id):
        """Save device ID to config file"""
        config = {'device_id': device_id}
        os.makedirs(os.path.dirname(self.CONFIG_FILE), exist_ok=True)
        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(config, f)
    
    def _load_config(self):
        """Load device configuration"""
        if os.path.exists(self.CONFIG_FILE):
            with open(self.CONFIG_FILE, 'r') as f:
                return json.load(f)
        return {}
    
    def get_device_id(self):
        return self.device_id
    
    def is_paired(self):
        """Check if device is already paired"""
        return 'paired' in self.config and self.config['paired']
    
    def save_pairing(self, credentials):
        """Save pairing information"""
        self.config['paired'] = True
        self.config['ssid'] = credentials['ssid']
        self.config['phone_address'] = credentials.get('phone_address')
        
        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(self.config, f)
    
    def cleanup(self):
        """Cleanup resources"""
        self.hardware.cleanup()
        self.network.cleanup()
    
    def shutdown(self):
        """Shutdown the device"""
        self.cleanup()
        os.system('sudo shutdown -h now')


class HardwareManager:
    """Manages all hardware components"""
    
    def __init__(self):
        self.sensors = SensorManager()
        self.camera = CameraManager()
        self.display = DisplayManager()
    
    def initialize(self):
        """Initialize hardware"""
        self.sensors.initialize()
        self.camera.initialize()
        self.display.turn_on()
    
    def start_voc_priming(self):
        self.sensors.start_priming()
    
    def are_voc_sensors_ready(self):
        return self.sensors.are_ready()
    
    def read_all_sensor_data(self, sensor_list):
        """Read VOC + environmental data together"""
        return self.sensors.read_all_data(sensor_list)
    def read_environment(self):
        """Just read temperature/humidity"""
        return self.sensors.read_environment()
    
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
        self.display.cleanup()


class NetworkManager:
    """Manages network communications"""
    
    def __init__(self, device_id):
        self.device_id = device_id
        self.ble = BLEManager(device_id)
        self.wifi = WiFiManager()
        self.mode = 'ble'  # Start with BLE
    
    def start_ble_advertising(self):
        return self.ble.start_advertising()
    
    def wait_for_pairing(self):
        return self.ble.wait_for_pairing()
    
    def stop_ble(self):
        self.ble.stop()
    
    def connect_wifi(self, ssid, password):
        success = self.wifi.connect(ssid, password)
        if success:
            self.mode = 'wifi'
        return success
    
    def start_wifi_server(self):
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
        self.ble.stop()
        self.wifi.stop()
