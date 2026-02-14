from datetime import datetime
import random
import time
import os
from io import BytesIO

try:
    from PIL import Image, ImageDraw
    from kivy.core.image import Image as CoreImage
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class MockDeviceManager:
    """Mock device manager for testing"""
    
    def __init__(self):
        self.device_id = "MINIK-TEST1234"
        self.config_data = {'paired': False}
        self.hardware = MockHardwareManager()
        self.network = MockNetworkManager(self.device_id)
    
    def get_device_id(self):
        return self.device_id
    
    def is_paired(self):
        return self.config_data.get('paired', False)
    
    def save_pairing(self, credentials):
        self.config_data['paired'] = True
        print(f"[MOCK] Pairing saved: {credentials}")
    
    def cleanup(self):
        print("[MOCK] Cleanup called")
    
    def shutdown(self):
        print("[MOCK] Shutdown requested")
        from kivy.app import App
        App.get_running_app().stop()


class MockHardwareManager:
    """Mock hardware manager"""
    
    def __init__(self):
        self.sensors = MockSensorManager()
        self.camera = MockCameraManager()
    
    def initialize(self):
        print("[MOCK] Hardware initializing...")
        time.sleep(0.5)
        print("[MOCK] Hardware initialized")
    
    def start_voc_priming(self):
        self.sensors.start_priming()
    
    def are_voc_sensors_ready(self):
        return self.sensors.are_ready()
    
    def read_voc_sensors(self, sensor_list):
        return self.sensors.read_sensors(sensor_list)
    
    def read_environment(self):
        return self.sensors.read_environment()
    
    def read_all_sensor_data(self, sensor_list):
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
        print("[MOCK] Hardware cleanup")


class MockSensorManager:
    """Mock sensor manager with realistic behavior"""
    
    def __init__(self):
        self.heating_start = None
        self.is_heating = False
        self.heat_time = 5  # 5 seconds in test mode instead of 180
    
    def initialize(self):
        print("[MOCK] Sensors initialized")
    
    def start_priming(self):
        self.is_heating = True
        self.heating_start = time.time()
        print(f"[MOCK] Sensors heating (will be ready in {self.heat_time}s)")
    
    def are_ready(self):
        if not self.is_heating or self.heating_start is None:
            return False
        
        elapsed = time.time() - self.heating_start
        if elapsed >= self.heat_time:
            print("[MOCK] Sensors are ready!")
            return True
        
        print(f"[MOCK] Sensors heating... {elapsed:.1f}/{self.heat_time}s")
        return False
    
    def read_environment(self):
        """Mock temperature and humidity"""
        return {
            'temperature': round(random.uniform(22, 28), 1),
            'humidity': round(random.uniform(45, 65), 1),
            'timestamp': datetime.now().isoformat()
        }
    
    def read_sensors(self, sensor_list):
        print(f"[MOCK] Reading sensors: {sensor_list}")
        readings = {}
        
        for sensor in sensor_list:
            readings[sensor] = {
                'voltage': round(random.uniform(0.5, 3.0), 3),
                'raw': random.randint(150, 900),
                'ppm': round(random.uniform(50, 800), 2),
                'resistance_ratio': round(random.uniform(0.5, 3.0), 3),
                'timestamp': datetime.now().isoformat()
            }
        
        return readings
    
    def read_all_data(self, sensor_list):
        """Mock combined reading"""
        env_data = self.read_environment()
        voc_data = self.read_sensors(sensor_list)
        
        return {
            'environment': env_data,
            'voc_sensors': voc_data,
            'timestamp': datetime.now().isoformat()
        }
    
    def generate_csv(self, sensor_data):
        import csv
        import tempfile
        
        # Create temp CSV
        fd, filename = tempfile.mkstemp(suffix='.csv', prefix='sensor_data_')
        
        with os.fdopen(fd, 'w', newline='') as csvfile:
            if 'environment' in sensor_data and 'voc_sensors' in sensor_data:
                env = sensor_data['environment']
                voc = sensor_data['voc_sensors']
                
                fieldnames = ['Temperature', 'Humidity'] + list(voc.keys())
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                row = {
                    'Temperature': env['temperature'],
                    'Humidity': env['humidity']
                }
                row.update({sensor: data['ppm'] for sensor, data in voc.items()})
                writer.writerow(row)
            else:
                fieldnames = list(sensor_data.keys())
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                row = {sensor: data['ppm'] for sensor, data in sensor_data.items()}
                writer.writerow(row)
        
        print(f"[MOCK] CSV generated: {filename}")
        return filename
    
    def cleanup(self):
        pass


class MockCameraManager:
    """Mock camera with preview simulation"""
    
    def __init__(self):
        self.preview_active = False
        self.frame_count = 0
    
    def initialize(self):
        print("[MOCK] Camera initialized")
    
    def start_preview(self):
        self.preview_active = True
        print("[MOCK] Camera preview started")
    
    def stop_preview(self):
        self.preview_active = False
        print("[MOCK] Camera preview stopped")
    
    def get_preview_texture(self):
        """Generate a mock preview texture"""
        if not self.preview_active or not HAS_PIL:
            return None
        
        self.frame_count += 1
        
        # Create a simple animated preview
        img = Image.new('RGB', (240, 180), color=(50, 50, 50))
        draw = ImageDraw.Draw(img)
        
        # Draw some shapes to simulate camera feed
        color = (random.randint(100, 200), random.randint(100, 200), random.randint(100, 200))
        draw.rectangle([80, 60, 160, 120], outline=color, width=3)
        draw.text((120, 90), "CAMERA", fill='white', anchor='mm')
        draw.text((120, 160), f"Frame {self.frame_count}", fill='gray', anchor='mm')
        
        # Convert to Kivy texture
        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        
        core_image = CoreImage(buf, ext='png')
        return core_image.texture
    
    def capture_image(self):
        """Generate a mock captured image"""
        import tempfile
        
        print("[MOCK] Capturing image...")
        time.sleep(0.5)
        
        if not HAS_PIL:
            fd, filename = tempfile.mkstemp(suffix='.jpg', prefix='capture_')
            os.close(fd)
            return filename
        
        # Create a mock food image
        img = Image.new('RGB', (640, 480), color=(180, 150, 120))
        draw = ImageDraw.Draw(img)
        
        draw.ellipse([220, 160, 420, 320], fill=(200, 100, 80))
        draw.text((320, 240), "FISH", fill='white', anchor='mm')
        draw.text((320, 440), "Mock Capture", fill='gray', anchor='mm')
        
        fd, filename = tempfile.mkstemp(suffix='.jpg', prefix='capture_')
        os.close(fd)
        img.save(filename)
        
        print(f"[MOCK] Image saved: {filename}")
        return filename
    
    def cleanup(self):
        self.stop_preview()


class MockNetworkManager:
    """Mock network manager"""
    
    def __init__(self, device_id):
        self.device_id = device_id
        self.mode = 'ble'
    
    def start_advertising(self):
        return self.start_ble_advertising()
    
    def start_ble_advertising(self):
        print(f"[MOCK] BLE advertising started for {self.device_id}")
        return True
    
    def wait_for_pairing(self):
        print("[MOCK] Waiting for pairing...")
        time.sleep(3)
        
        credentials = {
            'ssid': 'MockWiFi',
            'password': 'password123',
            'phone_address': '192.168.1.100'
        }
        
        print(f"[MOCK] Pairing received: {credentials['ssid']}")
        return credentials
    
    def stop(self):
        print("[MOCK] BLE/WiFi stopped")
    
    def connect(self, ssid, password):
        print(f"[MOCK] Connecting to WiFi: {ssid}")
        time.sleep(1)
        self.mode = 'wifi'
        print("[MOCK] WiFi connected")
        return True
    
    def start_server(self):
        print("[MOCK] WiFi server started")
    
    def send_image(self, image_path):
        print(f"[MOCK] Sending image: {image_path}")
        time.sleep(0.5)
        print("[MOCK] Image sent successfully")
        return True
    
    def wait_for_message(self, message_type):
        print(f"[MOCK] Waiting for {message_type}...")
        time.sleep(2)
        
        if message_type == 'cnn_result':
            result = {
                'food_type': random.choice(['Fish', 'Chicken', 'Beef', 'Pork']),
                'sensors': random.sample(['MQ2', 'MQ3', 'MQ4', 'MQ5', 'MQ135'], 3)
            }
        elif message_type == 'ml_result':
            result = {
                'food_type': 'Fish',
                'freshness': random.choice(['FRESH', 'MODERATE', 'SPOILED']),
                'confidence': round(random.uniform(75, 95), 1)
            }
        else:
            result = None
        
        print(f"[MOCK] {message_type} received: {result}")
        return result
    
    def send_file(self, file_path):
        print(f"[MOCK] Sending file: {file_path}")
        time.sleep(0.3)
        print("[MOCK] File sent successfully")
        return True
    
    def cleanup(self):
        print("[MOCK] Network cleanup")
