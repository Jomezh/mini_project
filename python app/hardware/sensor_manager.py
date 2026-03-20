import time
import os
import csv
import math
from datetime import datetime
import config

if config.IS_RASPBERRY_PI:
    import RPi.GPIO as GPIO
    import spidev
    import board
    import adafruit_dht

MOSFET_PIN   = 26
CS_MCP1      = 5
CS_MCP2      = 6
DHT_PIN_NUM  = 4

VREF         = 3.3
VCC_MQ       = 5.0
RL_KΩ        = 1.0
R_UPPER      = 20000.0
R_LOWER      = 10000.0
DIVIDER_GAIN = (R_UPPER + R_LOWER) / R_LOWER   # 3.0

WARMUP_SECS  = 30
N_SAMPLES    = 30
SAMPLE_DELAY = 1.0

MCP1_CHANNELS = ['MQ2','MQ3','MQ4','MQ5','MQ6','MQ8','MQ9','MQ135']
MCP2_CHANNELS = ['MQ136']
ALL_MQ        = MCP1_CHANNELS + MCP2_CHANNELS

_SPI_CANDIDATES = [(0, 1), (1, 0), (0, 0)]


class SensorManager:

    def __init__(self):
        self._priming_start = None
        self._dht           = None
        self._spi_bus       = None
        self._spi_dev       = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(MOSFET_PIN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(CS_MCP1,    GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(CS_MCP2,    GPIO.OUT, initial=GPIO.HIGH)
        self._dht = adafruit_dht.DHT11(getattr(board, f'D{DHT_PIN_NUM}'))
        self._spi_bus, self._spi_dev = self._detect_spi()
        print(f"[SENSORS] Initialized — will use /dev/spidev{self._spi_bus}.{self._spi_dev}")

    def _detect_spi(self):
        for bus, dev in _SPI_CANDIDATES:
            path = f'/dev/spidev{bus}.{dev}'
            if os.path.exists(path):
                print(f"[SENSORS] Found SPI device: {path}")
                return bus, dev
        available = [f for f in os.listdir('/dev') if f.startswith('spi')]
        raise OSError(
            f"No usable spidev found. Available: {available or 'none'}.\n"
            f"Enable SPI1 by adding 'dtoverlay=spi1-1cs' to /boot/config.txt and reboot."
        )

    def cleanup(self):
        self._mosfet_off()
        if self._dht:
            try: self._dht.exit()
            except Exception: pass
        try: GPIO.cleanup()
        except Exception: pass
        print("[SENSORS] Cleanup done")

    # ── SPI ───────────────────────────────────────────────────────────────────

    def _open_spi(self):
        spi = spidev.SpiDev()
        spi.open(self._spi_bus, self._spi_dev)
        spi.no_cs        = True
        spi.max_speed_hz = 1_350_000
        spi.mode         = 0b00
        return spi

    def _close_spi(self, spi):
        try: spi.close()
        except Exception: pass

    # ── ADC ───────────────────────────────────────────────────────────────────

    def _read_adc(self, spi, cs_pin, channel):
        GPIO.output(cs_pin, GPIO.LOW)
        cmd    = [1, (8 + channel) << 4, 0]
        result = spi.xfer2(cmd)
        GPIO.output(cs_pin, GPIO.HIGH)
        return ((result[1] & 3) << 8) | result[2]

    def _adc_to_rs(self, adc_raw):
        """ADC → RS in kΩ matching training data convention.
        V_pin = ADC / 1023 × VREF
        V_ao  = V_pin × 3          (undo 20k/10k divider)
        RS_kΩ = (VCC - V_ao) / V_ao × RL_kΩ
        """
        if adc_raw <= 0:
            return float('nan')
        v_pin = (adc_raw / 1023.0) * VREF
        v_ao  = v_pin * DIVIDER_GAIN
        if v_ao <= 0.0 or v_ao >= VCC_MQ:
            return float('nan')
        return (VCC_MQ - v_ao) / v_ao * RL_KΩ

    # ── Warmup ────────────────────────────────────────────────────────────────

    def start_priming(self):
        if self._priming_start is None:
            GPIO.output(MOSFET_PIN, GPIO.HIGH)
            self._priming_start = time.time()
            print(f"[SENSORS] MOSFET ON — warming up {WARMUP_SECS}s")

    def are_ready(self):
        if self._priming_start is None:
            return False
        return (time.time() - self._priming_start) >= WARMUP_SECS

    def warmup_remaining(self):
        if self._priming_start is None:
            return float(WARMUP_SECS)
        return max(0.0, WARMUP_SECS - (time.time() - self._priming_start))

    def _mosfet_off(self):
        try:
            GPIO.output(MOSFET_PIN, GPIO.LOW)
            self._priming_start = None
            print("[SENSORS] MOSFET OFF")
        except Exception:
            pass

    # ── DHT11 ─────────────────────────────────────────────────────────────────

    def _read_dht(self):
        for _ in range(3):
            try:
                t = self._dht.temperature
                h = self._dht.humidity
                if t is not None and h is not None:
                    return float(t), float(h)
            except RuntimeError:
                time.sleep(0.5)
        print("[SENSORS] DHT11 failed after 3 retries")
        return None, None

    # ── Main read ─────────────────────────────────────────────────────────────

    def read_all_data(self, sensor_list, progress_cb=None):
        remaining = self.warmup_remaining()
        if remaining > 0:
            print(f"[SENSORS] Warmup not done — waiting {remaining:.1f}s")
            time.sleep(remaining)

        # Only read MQ sensors the app requested — DHT11 always included
        mq_to_read = [s for s in sensor_list if s in ALL_MQ]
        raw        = {s: [] for s in mq_to_read + ['Temperature', 'Humidity']}

        print(f"[SENSORS] Opening SPI /dev/spidev{self._spi_bus}.{self._spi_dev}")
        print(f"[SENSORS] Reading sensors: {mq_to_read} + DHT11")
        spi = self._open_spi()

        try:
            print(f"[SENSORS] Sampling {N_SAMPLES} × {SAMPLE_DELAY}s")
            for i in range(N_SAMPLES):
                for ch, name in enumerate(MCP1_CHANNELS):
                    if name in mq_to_read:
                        raw[name].append(
                            self._adc_to_rs(self._read_adc(spi, CS_MCP1, ch))
                        )
                if 'MQ136' in mq_to_read:
                    raw['MQ136'].append(
                        self._adc_to_rs(self._read_adc(spi, CS_MCP2, 0))
                    )
                t, h = self._read_dht()
                if t is not None:
                    raw['Temperature'].append(t)
                    raw['Humidity'].append(h)
                if progress_cb:
                    progress_cb(i + 1, N_SAMPLES)
                if i < N_SAMPLES - 1:
                    time.sleep(SAMPLE_DELAY)
        finally:
            self._close_spi(spi)
            print("[SENSORS] SPI closed")

        self._mosfet_off()

        features = {}
        for sensor, values in raw.items():
            valid = [v for v in values
                     if v is not None and not (isinstance(v, float) and math.isnan(v))]
            if not valid:
                print(f"[SENSORS] No valid data for {sensor} — using 0")
                valid = [0.0]
            n    = len(valid)
            mean = sum(valid) / n
            std  = math.sqrt(sum((x - mean) ** 2 for x in valid) / n)
            features[f'{sensor}_mean'] = round(mean, 4)
            features[f'{sensor}_std']  = round(std,  4)
            features[f'{sensor}_max']  = round(max(valid), 4)

        print(f"[SENSORS] Done — {len(features)} features computed")
        return {'raw_samples': raw, 'features': features}

    # ── CSV ───────────────────────────────────────────────────────────────────

    def generate_csv(self, data, sensor_list):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(base_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        path      = os.path.join(data_dir, f'sensors_{timestamp}.csv')

        # MQ columns in app-defined order (matches RF model training order)
        mq_sensors   = [s for s in sensor_list if s in ALL_MQ]
        dynamic_cols = []
        for sensor in mq_sensors:
            dynamic_cols.append(f'{sensor}_mean')
            dynamic_cols.append(f'{sensor}_std')
            dynamic_cols.append(f'{sensor}_max')
        # DHT11 always last — Humidity then Temperature
        for stat in ['mean', 'std', 'max']:
            dynamic_cols.append(f'Humidity_{stat}')
        for stat in ['mean', 'std', 'max']:
            dynamic_cols.append(f'Temperature_{stat}')

        features = data.get('features', {})
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(dynamic_cols)
            writer.writerow([f"{features.get(col, 0.0):.4f}" for col in dynamic_cols])

        print(f"[SENSORS] CSV columns: {dynamic_cols}")
        print(f"[SENSORS] CSV saved: {os.path.basename(path)}")
        return path
