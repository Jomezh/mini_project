import time
import os
import csv
import json
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



DEFAULT_WARMUP_SECS = 30



N_SAMPLES    = 30
SAMPLE_DELAY = 1.0



MCP1_CHANNELS = ['MQ2', 'MQ3', 'MQ4', 'MQ5', 'MQ6', 'MQ8', 'MQ9', 'MQ135']
MCP2_CHANNELS = ['MQ136']
ALL_MQ        = MCP1_CHANNELS + MCP2_CHANNELS



_SPI_CANDIDATES = [(0, 1), (1, 0), (0, 0)]



BASELINE_RATIO_TOLERANCE = 15.0
LOW_SIGNAL_THRESHOLD     = 50
LOW_SIGNAL_STABLE_RANGE  = 5



CLEAN_AIR_RATIO = {
    'MQ135': 3.6, 'MQ136': 3.4, 'MQ2': 9.8,  'MQ3': 60.0,
    'MQ4':   4.4, 'MQ5':   6.5, 'MQ6': 10.0, 'MQ8': 70.0, 'MQ9': 9.9,
}

# FIX: DHT11 reads in a separate pass after SPI closes
_DHT_SAMPLES  = 5
_DHT_INTERVAL = 2.0   # DHT11 spec minimum interval between reads



class SensorManager:


    def __init__(self):
        self._priming_start = None
        self._dht           = None
        self._spi_bus       = None
        self._spi_dev       = None
        self._cal           = None
        self._initialized   = False


    # ── Lifecycle ─────────────────────────────────────────────────────────────


    def initialize(self):
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(MOSFET_PIN, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(CS_MCP1,    GPIO.OUT, initial=GPIO.HIGH)
            GPIO.setup(CS_MCP2,    GPIO.OUT, initial=GPIO.HIGH)
        except Exception as e:
            print(f"[SENSORS] ⚠ GPIO setup failed: {e}")


        try:
            self._dht = adafruit_dht.DHT11(getattr(board, f'D{DHT_PIN_NUM}'))
        except Exception as e:
            print(f"[SENSORS] ⚠ DHT11 init failed: {e}")


        try:
            self._spi_bus, self._spi_dev = self._detect_spi()
            self._initialized = True
            print(f"[SENSORS] Initialized — SPI /dev/spidev{self._spi_bus}.{self._spi_dev}")
        except OSError as e:
            print(f"[SENSORS] ⚠ SPI detect failed: {e}")
            print(f"[SENSORS]   Ensure 'dtoverlay=spi1-1cs' is in /boot/config.txt")
            print(f"[SENSORS]   Will retry on first sensor read")


        self._cal = self._load_calibration()


    def _detect_spi(self):
        for bus, dev in _SPI_CANDIDATES:
            path = f'/dev/spidev{bus}.{dev}'
            if os.path.exists(path):
                print(f"[SENSORS] Found SPI: {path}")
                return bus, dev
        available = [f for f in os.listdir('/dev') if f.startswith('spi')]
        raise OSError(
            f"No spidev found. Available: {available or 'none'}.\n"
            f"Add 'dtoverlay=spi1-1cs' to /boot/config.txt and reboot."
        )


    def _load_calibration(self):
        cal_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'calibration.json'
        )
        if os.path.exists(cal_path):
            try:
                with open(cal_path) as f:
                    cal = json.load(f)
                print(f"[SENSORS] Calibration loaded : {cal['timestamp']}")
                print(f"[SENSORS] Recorded warmup    : {cal.get('warmup_sec', '?')}s")
                low = [n for n, v in cal.get('sensors', {}).items()
                       if v.get('low_signal')]
                if low:
                    print(f"[SENSORS] Low-signal sensors (count-based check): {low}")
                return cal
            except Exception as e:
                print(f"[SENSORS] ⚠ Could not load calibration.json: {e}")
        else:
            print(f"[SENSORS] ⚠ No calibration.json — run: python mq_calibrate.py")
            print(f"[SENSORS]   Falling back to {DEFAULT_WARMUP_SECS}s timer warmup")
        return None


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
        if self._spi_bus is None or self._spi_dev is None:
            print("[SENSORS] SPI not initialized — retrying detect...")
            try:
                self._spi_bus, self._spi_dev = self._detect_spi()
                self._initialized = True
            except OSError as e:
                raise RuntimeError(
                    f"[SENSORS] SPI unavailable: {e}\n"
                    f"Check: dtoverlay=spi1-1cs in /boot/config.txt, then reboot."
                ) from e


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
        if adc_raw <= 0:
            return float('nan')
        v_pin = (adc_raw / 1023.0) * VREF
        v_ao  = v_pin * DIVIDER_GAIN
        if v_ao <= 0.0 or v_ao >= VCC_MQ:
            return float('nan')
        return (VCC_MQ - v_ao) / v_ao * RL_KΩ


    def _read_raw(self, name):
        spi = self._open_spi()
        try:
            if name in MCP1_CHANNELS:
                ch  = MCP1_CHANNELS.index(name)
                raw = self._read_adc(spi, CS_MCP1, ch)
            else:
                ch  = MCP2_CHANNELS.index(name)
                raw = self._read_adc(spi, CS_MCP2, ch)
        finally:
            self._close_spi(spi)
        return self._adc_to_rs(raw), raw


    # ── Warmup ────────────────────────────────────────────────────────────────


    def _get_warmup_secs(self):
        if self._cal:
            return self._cal.get('warmup_sec', DEFAULT_WARMUP_SECS)
        return DEFAULT_WARMUP_SECS


    def start_priming(self):
        if self._priming_start is None:
            GPIO.output(MOSFET_PIN, GPIO.HIGH)
            self._priming_start = time.time()
            src = "calibrated" if self._cal else "default"
            print(f"[SENSORS] MOSFET ON — warming up "
                  f"{self._get_warmup_secs()}s ({src})")


    def are_ready(self):
        if self._priming_start is None:
            return False
        if self._warmup_elapsed() < self._get_warmup_secs():
            return False
        if self._cal is None:
            return True
        return self._all_sensors_at_baseline()


    def _all_sensors_at_baseline(self):
        if not self._cal:
            return True
        for name in ALL_MQ:
            sensor_cal = self._cal.get('sensors', {}).get(name)
            if sensor_cal is None:
                continue
            r0         = sensor_cal.get('R0_kΩ', 0)
            low_signal = sensor_cal.get('low_signal', False)
            if r0 <= 0:
                continue
            try:
                rs, raw = self._read_raw(name)
            except Exception:
                continue


            if low_signal:
                raws = [raw]
                spi  = self._open_spi()
                cs   = CS_MCP1 if name in MCP1_CHANNELS else CS_MCP2
                ch   = (MCP1_CHANNELS.index(name) if name in MCP1_CHANNELS
                        else MCP2_CHANNELS.index(name))
                try:
                    for _ in range(4):
                        raws.append(self._read_adc(spi, cs, ch))
                        time.sleep(0.1)
                finally:
                    self._close_spi(spi)
                if max(raws) - min(raws) > LOW_SIGNAL_STABLE_RANGE:
                    print(f"[SENSORS] {name} not stable "
                          f"(count range {max(raws)-min(raws)} > "
                          f"{LOW_SIGNAL_STABLE_RANGE})")
                    return False
            else:
                if math.isnan(rs):
                    continue
                if not self._ratio_ok(rs, r0, name):
                    print(f"[SENSORS] {name} not at baseline "
                          f"(Rs={rs:.4f}kΩ R0={r0:.4f}kΩ "
                          f"ratio={rs/r0:.3f} "
                          f"expected≈{CLEAN_AIR_RATIO.get(name, 1):.1f})")
                    return False
        return True


    def _ratio_ok(self, rs, r0, name):
        current_ratio  = rs / r0
        expected_ratio = CLEAN_AIR_RATIO.get(name, 1.0)
        dev_pct        = abs(current_ratio - expected_ratio) / expected_ratio * 100.0
        return dev_pct < BASELINE_RATIO_TOLERANCE


    def _warmup_elapsed(self):
        if self._priming_start is None:
            return 0.0
        return time.time() - self._priming_start


    def warmup_remaining(self):
        return max(0.0, self._get_warmup_secs() - self._warmup_elapsed())


    def _mosfet_off(self):
        try:
            GPIO.output(MOSFET_PIN, GPIO.LOW)
            self._priming_start = None
            print("[SENSORS] MOSFET OFF")
        except Exception:
            pass


    # ── DHT11 ─────────────────────────────────────────────────────────────────


    def _read_dht(self):
        if self._dht is None:
            print("[SENSORS] DHT11 not initialized — skipping")
            return None, None
        for attempt in range(3):
            try:
                t = self._dht.temperature
                h = self._dht.humidity
                if t is not None and h is not None:
                    return float(t), float(h)
                print(f"[SENSORS] DHT11 returned None values (attempt {attempt + 1}/3)")
            except RuntimeError as e:
                print(f"[SENSORS] DHT11 RuntimeError attempt {attempt + 1}/3: {e}")
                time.sleep(2.0)   # FIX: was 0.5s — DHT11 spec minimum is 2s
        print("[SENSORS] DHT11 failed after 3 retries")
        return None, None


    # ── Main read ─────────────────────────────────────────────────────────────


    def read_all_data(self, sensor_list, progress_cb=None):
        remaining = self.warmup_remaining()
        if remaining > 0:
            print(f"[SENSORS] Warmup not done — waiting {remaining:.1f}s")
            time.sleep(remaining)

        mq_to_read = [s for s in sensor_list if s in ALL_MQ]
        raw        = {s: [] for s in mq_to_read + ['Temperature', 'Humidity']}

        print(
            f"[SENSORS] Opening SPI /dev/spidev{self._spi_bus}.{self._spi_dev}"
            if self._spi_bus is not None
            else "[SENSORS] Opening SPI (lazy detect)..."
        )
        print(f"[SENSORS] Reading: {mq_to_read}")
        spi = self._open_spi()

        try:
            # FIX: DHT11 removed from this loop — SPI DMA disrupts adafruit_dht
            # bit-bang timing causing consistent RuntimeError → all-zero readings
            print(f"[SENSORS] Sampling MQ {N_SAMPLES} × {SAMPLE_DELAY}s")
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
                if progress_cb:
                    progress_cb(i + 1, N_SAMPLES)
                if i < N_SAMPLES - 1:
                    time.sleep(SAMPLE_DELAY)
        finally:
            self._close_spi(spi)
            print("[SENSORS] SPI closed")

        # FIX: DHT11 reads happen here, after SPI is fully closed
        # adafruit_dht bit-banging needs uninterrupted GPIO timing
        print(f"[SENSORS] Reading DHT11 ({_DHT_SAMPLES} samples × {_DHT_INTERVAL}s)...")
        for i in range(_DHT_SAMPLES):
            t, h = self._read_dht()
            if t is not None:
                raw['Temperature'].append(t)
                raw['Humidity'].append(h)
                print(f"[SENSORS] DHT11 sample {i + 1}: {t}°C  {h}%")
            if i < _DHT_SAMPLES - 1:
                time.sleep(_DHT_INTERVAL)

        if not raw['Temperature']:
            print("[SENSORS] ⚠ DHT11 returned no valid readings — check wiring on GPIO 4")
        else:
            print(f"[SENSORS] DHT11 done — {len(raw['Temperature'])} valid samples")

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


    def generate_csv(self, data, sensor_list=None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(base_dir, 'data')
        os.makedirs(data_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        path      = os.path.join(data_dir, f'sensors_{timestamp}.csv')

        features     = data.get('features', {})
        all_keys     = list(features.keys())
        mq_keys      = [k for k in all_keys if not k.startswith(('Temperature', 'Humidity'))]
        env_keys     = [k for k in all_keys if k.startswith(('Temperature', 'Humidity'))]
        dynamic_cols = mq_keys + env_keys

        with open(path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(dynamic_cols)
            writer.writerow([f"{features.get(col, 0.0):.4f}" for col in dynamic_cols])

        print(f"[SENSORS] CSV saved: {os.path.basename(path)}")
        return path