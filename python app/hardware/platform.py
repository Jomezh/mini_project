# hardware/platform.py
import os

def is_pi():
    try:
        with open("/proc/device-tree/model", "r") as f:
            return "Raspberry Pi" in f.read()
    except FileNotFoundError:
        return False
