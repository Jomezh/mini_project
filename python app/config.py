"""
Hardware configuration flags
Toggle between real and mock hardware
"""

import os

# ============================================
# HARDWARE CONFIGURATION
# Change these flags as you add hardware
# ============================================

USE_REAL_SENSORS = False   # MCP3008 + MQ sensors
USE_REAL_DHT11 = False     # DHT11 temp/humidity
USE_REAL_CAMERA = True     # Raspberry Pi Camera
USE_REAL_NETWORK = False   # BLE + WiFi

# ============================================
# Auto-detection & overrides
# ============================================

# Detect if running on Raspberry Pi
try:
    with open('/proc/device-tree/model', 'r') as f:
        IS_RASPBERRY_PI = 'Raspberry Pi' in f.read()
except:
    IS_RASPBERRY_PI = False

# Force mock mode for desktop testing
if os.environ.get('MINIK_TEST_MODE') == '1':
    USE_REAL_SENSORS = False
    USE_REAL_DHT11 = False
    USE_REAL_CAMERA = False
    USE_REAL_NETWORK = False
    print("[CONFIG] TEST MODE - all hardware mocked")

# Display current configuration
def print_config():
    print("="*50)
    print("Hardware Configuration:")
    print("="*50)
    print(f"  Platform:    {'Raspberry Pi' if IS_RASPBERRY_PI else 'Desktop'}")
    print(f"  VOC Sensors: {'REAL (MCP3008)' if USE_REAL_SENSORS else 'MOCK'}")
    print(f"  DHT11:       {'REAL' if USE_REAL_DHT11 else 'MOCK'}")
    print(f"  Camera:      {'REAL (PiCamera)' if USE_REAL_CAMERA else 'MOCK'}")
    print(f"  Network:     {'REAL (BLE/WiFi)' if USE_REAL_NETWORK else 'MOCK'}")
    print("="*50)

if __name__ == '__main__':
    print_config()
