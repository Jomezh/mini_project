# hardware/power.py
import os
from hardware.platform import is_pi

def shutdown():
    """
    Gracefully shut down the system.
    On PC: mock.
    On Pi: real shutdown.
    """
    if is_pi():
        os.system("sudo shutdown -h now")
    else:
        print("[MOCK] Shutdown requested")
