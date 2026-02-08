# hardware/display.py
from hardware.platform import is_pi

class Display:
    def __init__(self):
        self.initialized = False
        if is_pi():
            self._init_real()
        else:
            self._init_mock()

    def _init_real(self):
        # Real SPI display init comes later
        # (framebuffer driver already active)
        self.initialized = True
        print("SPI display initialized")

    def _init_mock(self):
        self.initialized = True
        print("[MOCK] Display initialized")

    def backlight(self, on: bool):
        if not self.initialized:
            return
        if is_pi():
            print(f"Backlight {'ON' if on else 'OFF'}")
            # GPIO control later if needed
        else:
            print(f"[MOCK] Backlight {'ON' if on else 'OFF'}")
