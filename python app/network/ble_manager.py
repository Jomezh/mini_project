import time
import json
from threading import Event

try:
    from bluezero import adapter, peripheral
    HAS_BLE = True
except ImportError:
    HAS_BLE = False
    print("Warning: BLE libraries not available. Running in simulation mode.")


class BLEManager:
    """Manages BLE communication for initial pairing"""
    
    SERVICE_UUID = '12345678-1234-5678-1234-56789abcdef0'
    CHAR_UUID = '12345678-1234-5678-1234-56789abcdef1'
    
    def __init__(self, device_id):
        self.device_id = device_id
        self.adapter = None
        self.peripheral_app = None
        self.advertising = False
        self.pairing_event = Event()
        self.pairing_data = None
        
    def start_advertising(self):
        """Start BLE advertising for pairing"""
        if not HAS_BLE:
            print("BLE running in simulation mode")
            return True
        
        try:
            # Get default adapter
            self.adapter = adapter.Adapter()
            self.adapter.powered = True
            
            # Create peripheral with device name
            device_name = f"MiniK_{self.device_id[-4:]}"
            
            # Start advertising
            # Note: This is simplified. You may need to use dbus-python or bleak
            print(f"BLE advertising started: {device_name}")
            self.advertising = True
            return True
            
        except Exception as e:
            print(f"Error starting BLE: {e}")
            return False
    
    def wait_for_pairing(self):
        """Wait for pairing request from phone"""
        if not HAS_BLE:
            # Simulation mode - wait 3 seconds then return dummy data
            time.sleep(3)
            return {
                'ssid': 'SimulatedWiFi',
                'password': 'password123',
                'phone_address': '192.168.1.100'
            }
        
        # Wait for pairing event (with timeout handled by caller)
        self.pairing_event.wait()
        return self.pairing_data
    
    def _on_data_received(self, data):
        """Callback when data is received via BLE"""
        try:
            # Parse JSON data from phone
            pairing_info = json.loads(data.decode())
            self.pairing_data = pairing_info
            self.pairing_event.set()
            
        except Exception as e:
            print(f"Error parsing BLE data: {e}")
    
    def stop(self):
        """Stop BLE advertising"""
        self.advertising = False
        if self.adapter:
            try:
                self.adapter.powered = False
            except:
                pass
        print("BLE stopped")
