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

# ── Pin / circuit constants ───────────────────────────────────────────────────
MOSFET_PIN   = 26
CS_MCP1      = 5       # GPIO 5 → MCP3008 #1  (MQ2,MQ3,MQ4,MQ5,MQ6,MQ8,MQ9,MQ135)
CS_MCP2      = 6       # GPIO 6 → MCP3008 #2  (MQ136)
DHT_PIN_NUM  = 4

VREF         = 3.3     # MCP3008 reference voltage
VCC_MQ       = 5.0     # MQ sensor supply voltage
RL_KΩ        = 1.0     # Load resistor in kΩ — training data uses kΩ unit
R_UPPER      = 20000.0 # Voltage-divider top    (MQ AO → MCP pin)
R_LOWER      = 10000.0 # Voltage-divider bottom (MCP pin → GND)
DIVIDER_GAIN = (R_UPPER + R_LOWER) / R_LOWER   # 3.0
#
#  MQ AO ──[20kΩ]──┬── MCP3008 CHx
#                  │
#               [10kΩ]
#                  │
#                 GND
#
#  V_ao  = V_pin × 3          (undo divider)
#  RS_kΩ = (VCC - V_ao) / V_ao × RL_kΩ    → result in kΩ, matches training data

# ── Timing ────────────────────────────────────────────────────────────────────
WARMUP_SECS  = 30
N_SAMPLES    = 30
SAMPLE_DELAY = 1.0

# ── Channel maps ──────────────────────────────────────────────────────────────
MCP1_CHANNELS = ['MQ2','MQ3','MQ4','MQ5','MQ6','MQ8','MQ9','MQ135']
MCP2_CHANNELS = ['MQ136']

# ── CSV columns — must match model_feature_33.pkl exactly ────────────────────
CSV_COLUMNS = [
    'MQ135_mean','MQ135_std','MQ135_max',
    'MQ136_mean','MQ136_std','MQ136_max',
    'MQ2_mean',  'MQ2_std',  'MQ2_max',
    'MQ3_mean',  'MQ3_std',  'MQ3_max',
    'MQ4_mean',  'MQ4_std',  'MQ4_max',
    'MQ5_mean',  'MQ5_std',  'MQ5_max',
    'MQ6_mean',  'MQ6_std',  'MQ6_max',
    'MQ8_mean',  'MQ8_std',  'MQ8_max',
    'MQ9_mean',  'MQ9_std',  'MQ9_max',
    'Humidity_mean',    'Humidity_std',    'Humidity_max',
    'Temperature_mean', 'Temperature_std', 'Temperature_max',
]


class SensorManager:

    def __init__(self):
        self._priming_start = None
        self._spi           = None
        self._dht           = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def initialize(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(MOSFET_PIN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(CS_MCP1,    GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setup(CS_MCP2,    GPIO.OUT, initial=GPIO.HIGH)
        self._spi = spidev.SpiDev()
        self._spi.open(0, 0)
        self._spi.max_speed_hz = 1_350_000
        self._spi.mode = 0b00
        self._dht = adafruit_dht.DHT11(getattr(board, f'D{DHT_PIN_NUM}'))
        print("[SENSORS] Initialized — MOSFET off")

    def cleanup(self):
        self._mosfet_off()
        if self._spi:
            try: self._spi.close()
            except Exception: pass
        if self._dht:
            try: self._dht.exit()
            except Exception: pass
        try: GPIO.cleanup()
        except Exception: pass
        print("[SENSORS] Cleanup done")

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

    # ── ADC / SPI ─────────────────────────────────────────────────────────────

    def _read_adc(self, cs_pin, channel):
        GPIO.output(cs_pin, GPIO.LOW)
        cmd    = [1, (8 + channel) << 4, 0]
        result = self._spi.xfer2(cmd)
        GPIO.output(cs_pin, GPIO.HIGH)
        return ((result[1] & 3) << 8) | result[2]

    def _adc_to_rs(self, adc_raw):
        """Convert raw ADC → sensor resistance RS in kΩ.

        Matches training data convention exactly:
          V_pin = ADC / 1023 × VREF        (MCP3008 pin voltage, after divider)
          V_ao  = V_pin × DIVIDER_GAIN     (undo 20k/10k divider → real MQ AO voltage)
          RS_kΩ = (VCC_MQ − V_ao) / V_ao × RL_kΩ
        Result in kΩ — identical scale to training CSV (values ~10–45 range).
        """
        if adc_raw <= 0:
            return float('nan')
        v_pin = (adc_raw / 1023.0) * VREF
        v_ao  = v_pin * DIVIDER_GAIN
        if v_ao <= 0.0 or v_ao >= VCC_MQ:
            return float('nan')
        return (VCC_MQ - v_ao) / v_ao * RL_KΩ

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

        raw = {s: [] for s in MCP1_CHANNELS + MCP2_CHANNELS + ['Temperature', 'Humidity']}

        print(f"[SENSORS] Sampling {N_SAMPLES} × {SAMPLE_DELAY}s")

        for i in range(N_SAMPLES):
            for ch, name in enumerate(MCP1_CHANNELS):
                raw[name].append(self._adc_to_rs(self._read_adc(CS_MCP1, ch)))
            raw['MQ136'].append(self._adc_to_rs(self._read_adc(CS_MCP2, 0)))
            t, h = self._read_dht()
            if t is not None:
                raw['Temperature'].append(t)
                raw['Humidity'].append(h)
            if progress_cb:
                progress_cb(i + 1, N_SAMPLES)
            if i < N_SAMPLES - 1:
                time.sleep(SAMPLE_DELAY)

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

    def generate_csv(self, data):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(base_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        path      = os.path.join(data_dir, f'sensors_{timestamp}.csv')
        features  = data.get('features', {})
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_COLUMNS)
            writer.writerow([f"{features.get(col, 0.0):.4f}" for col in CSV_COLUMNS])
        print(f"[SENSORS] CSV saved: {os.path.basename(path)}")
        return path
