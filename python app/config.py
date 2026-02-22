import os

# ============================================
# HARDWARE CONFIGURATION
# ============================================
USE_REAL_SENSORS  = False
USE_REAL_DHT11    = False
USE_REAL_CAMERA   = True
USE_REAL_NETWORK  = False
SHOW_RESET_BUTTON = True

# ── Mock simulation flags ────────────────────
# Only used when USE_REAL_NETWORK = False

# True  → BLE scan finds the phone (normal boot)
# False → BLE scan finds nothing  → QR screen shown
MOCK_BLE_DEVICE_FOUND = True

# True  → WiFi/hotspot connect succeeds
# False → hotspot is off → triggers retry/prompt flow
MOCK_HOTSPOT_ON = True

# ============================================
# Auto-detection
# ============================================
try:
    with open('/proc/device-tree/model', 'r') as f:
        IS_RASPBERRY_PI = 'Raspberry Pi' in f.read()
except:
    IS_RASPBERRY_PI = False

if os.environ.get('MINIK_TEST_MODE') == '1':
    USE_REAL_SENSORS          = False
    USE_REAL_DHT11            = False
    USE_REAL_CAMERA           = False
    USE_REAL_NETWORK          = False
    MOCK_BLE_DEVICE_FOUND     = False   # Test mode starts from QR
    print("[CONFIG] TEST MODE - all hardware mocked")


def print_config():
    print("=" * 50)
    print("Hardware Configuration:")
    print("=" * 50)
    print(f"  Platform:       {'Raspberry Pi' if IS_RASPBERRY_PI else 'Desktop'}")
    print(f"  VOC Sensors:    {'REAL' if USE_REAL_SENSORS else 'MOCK'}")
    print(f"  DHT11:          {'REAL' if USE_REAL_DHT11 else 'MOCK'}")
    print(f"  Camera:         {'REAL' if USE_REAL_CAMERA else 'MOCK'}")
    print(f"  Network:        {'REAL' if USE_REAL_NETWORK else 'MOCK'}")
    if not USE_REAL_NETWORK:
        print(f"  Mock BLE scan:  {'FOUND' if MOCK_BLE_DEVICE_FOUND else 'NOT FOUND (→ QR)'}")
        print(f"  Mock Hotspot:   {'ON' if MOCK_HOTSPOT_ON else 'OFF (→ retry prompt)'}")
    print(f"  Reset Button:   {'Visible' if SHOW_RESET_BUTTON else 'Hidden'}")
    print("=" * 50)


if __name__ == '__main__':
    print_config()
