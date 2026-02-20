"""
Run this to reset pairing state:
    python3 utils/reset_pairing.py
"""
import os
import json

CONFIG_FILE = os.path.expanduser('~/mini_project/minik_config.json')

def reset():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
        
        device_id = data.get('device_id', 'UNKNOWN')
        
        # Keep device ID, clear pairing info only
        new_data = {'device_id': device_id}
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(new_data, f)
        
        print(f"Pairing reset. Device ID kept: {device_id}")
    else:
        print("No config found - already unpaired")

if __name__ == '__main__':
    reset()
