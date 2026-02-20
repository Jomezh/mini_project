"""
Hardware configuration flags
Toggle between real and mock hardware
"""
import os

# ============================================
# HARDWARE CONFIGURATION
# ============================================
USE_REAL_SENSORS = False
USE_REAL_DHT11   = False
USE_REAL_CAMERA  = True
USE_REAL_NETWORK = False

# Show reset pairing button on pairing screen
# Set False for production builds
SHOW_RESET_BUTTON = True

# ============================================
# Auto-detection
# ============================================
try:
    with open('/proc/device-tree/model', 'r') as f:
        IS_RASPBERRY_PI = 'Raspberry Pi' in f.read()
except:
    IS_RASPBERRY_PI = False

# Force mock mode via environment variable
if os.environ.get('MINIK_TEST_MODE') == '1':
    USE_REAL_SENSORS = False
    USE_REAL_DHT11   = False
    USE_REAL_CAMERA  = False
    USE_REAL_NETWORK = False
    print("[CONFIG] TEST MODE - all hardware mocked")

def print_config():
    print("=" * 50)
    print("Hardware Configuration:")
    print("=" * 50)
    print(f"  Platform:    {'Raspberry Pi' if IS_RASPBERRY_PI else 'Desktop'}")
    print(f"  VOC Sensors: {'REAL (MCP3008)' if USE_REAL_SENSORS else 'MOCK'}")
    print(f"  DHT11:       {'REAL' if USE_REAL_DHT11 else 'MOCK'}")
    print(f"  Camera:      {'REAL (PiCamera)' if USE_REAL_CAMERA else 'MOCK'}")
    print(f"  Network:     {'REAL (BLE/WiFi)' if USE_REAL_NETWORK else 'MOCK'}")
    print(f"  Reset Btn:   {'Visible' if SHOW_RESET_BUTTON else 'Hidden'}")
    print("=" * 50)

if __name__ == '__main__':
    print_config()
