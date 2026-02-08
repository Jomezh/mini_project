# hardware/adc.py
import random
from hardware.platform import is_pi

class ADC:
    def __init__(self):
        if is_pi():
            self._init_real()
        else:
            self._init_mock()

    def _init_real(self):
        # SPI init later
        self.ready = True
        print("ADC initialized (real)")

    def _init_mock(self):
        self.ready = True
        print("[MOCK] ADC initialized")

    def read_all(self):
        """
        Return raw sensor readings.
        """
        if is_pi():
            return self._read_real()
        else:
            return self._read_mock()

    def _read_mock(self):
        return {
            "MQ2": random.randint(200, 400),
            "MQ3": random.randint(150, 350),
            "MQ135": random.randint(300, 600),
        }

    def _read_real(self):
        # MCP3008 SPI reads later
        pass
