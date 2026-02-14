import time
import csv
import os
from datetime import datetime

try:
    import busio
    import digitalio
    import board
    from adafruit_mcp3xxx.mcp3008 import MCP3008
    from adafruit_mcp3xxx.analog_in import AnalogIn
    import adafruit_dht  # DHT11 library
    HAS_HARDWARE = True
except ImportError:
    HAS_HARDWARE = False
    print("Warning: Hardware libraries not available. Running in simulation mode.")


class SensorManager:
    """Manages MQ VOC sensors via dual MCP3008 ADCs + DHT11 temp/humidity"""
    
    # MQ sensor heating time (seconds)
    HEATING_TIME = 180  # 3 minutes for MQ sensors to stabilize
    STABILITY_THRESHOLD = 0.05  # 5% variation for stability
    
    # NOTE: DHT11_PIN moved to __init__ to avoid hardware access at class level
    
    # Sensor pin mapping (same as before)
    SENSOR_MAP = {
        # First MCP3008 (chip 0)
        'MQ2': (0, 0),   # Combustible gases, smoke
        'MQ3': (0, 1),   # Alcohol, ethanol
        'MQ4': (0, 2),   # Methane, CNG
        'MQ5': (0, 3),   # LPG, natural gas
        'MQ6': (0, 4),   # LPG, butane
        'MQ7': (0, 5),   # Carbon monoxide
        'MQ8': (0, 6),   # Hydrogen
        'MQ9': (0, 7),   # CO, combustible gases
        
        # Second MCP3008 (chip 1)
        'MQ135': (1, 0), # Air quality
        'MQ136': (1, 1), # Hydrogen sulfide
        'MQ137': (1, 2), # Ammonia
        'MQ138': (1, 3), # Benzene, toluene
    }
    
    VREF = 3.3
    
    def __init__(self):
        self.initialized = False
        self.heating_start_time = None
        self.is_heating = False
        self.mcp_chips = []
        self.channels = {}
        self.baseline_readings = {}
        
        # DHT11 sensor - initialize only if hardware available
        self.dht_device = None
        self.dht_pin = None
        self.last_temp = None
        self.last_humidity = None
        
        # Set DHT11 pin only if hardware is available
        if HAS_HARDWARE:
            try:
                self.dht_pin = board.D4  # GPIO 4 by default
            except:
                self.dht_pin = None
        
    def initialize(self):
        """Initialize SPI (MCP3008) and GPIO (DHT11)"""
        if not HAS_HARDWARE:
            self.initialized = True
            print("Running in simulation mode (no hardware)")
            return
        
        try:
            # Initialize MCP3008 chips
            spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
            cs0 = digitalio.DigitalInOut(board.CE0)
            cs1 = digitalio.DigitalInOut(board.CE1)
            
            mcp0 = MCP3008(spi, cs0)
            mcp1 = MCP3008(spi, cs1)
            self.mcp_chips = [mcp0, mcp1]
            
            # Setup VOC sensor channels
            for sensor_name, (chip_num, channel_num) in self.SENSOR_MAP.items():
                if chip_num < len(self.mcp_chips):
                    chip = self.mcp_chips[chip_num]
                    channel = AnalogIn(chip, getattr(MCP3008, f'P{channel_num}'))
                    self.channels[sensor_name] = channel
            
            # Initialize DHT11 (only if pin was set)
            if self.dht_pin:
                self.dht_device = adafruit_dht.DHT11(self.dht_pin)
            
            self.initialized = True
            print(f"Sensor manager initialized:")
            print(f"  - {len(self.mcp_chips)} MCP3008 chips")
            print(f"  - {len(self.channels)} VOC sensors")
            if self.dht_device:
                print(f"  - DHT11 on GPIO {self.dht_pin}")
            
        except Exception as e:
            print(f"Error initializing sensors: {e}")
            self.initialized = False
    
    def read_environment(self):
        """Read temperature and humidity from DHT11"""
        if not HAS_HARDWARE or not self.dht_device:
            # Simulation mode
            import random
            return {
                'temperature': round(random.uniform(20, 30), 1),
                'humidity': round(random.uniform(40, 70), 1),
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            temperature = self.dht_device.temperature
            humidity = self.dht_device.humidity
            
            # Cache valid readings (DHT11 can be flaky)
            if temperature is not None:
                self.last_temp = temperature
            if humidity is not None:
                self.last_humidity = humidity
            
            return {
                'temperature': round(temperature if temperature else self.last_temp, 1),
                'humidity': round(humidity if humidity else self.last_humidity, 1),
                'timestamp': datetime.now().isoformat()
            }
            
        except RuntimeError as e:
            # DHT11 often needs retry
            print(f"DHT11 read error (will retry): {e}")
            return {
                'temperature': self.last_temp or 25.0,
                'humidity': self.last_humidity or 50.0,
                'timestamp': datetime.now().isoformat(),
                'error': 'retry'
            }
    
    def read_sensors(self, sensor_list):
        """Read specified VOC sensors"""
        readings = {}
        
        if HAS_HARDWARE and self.initialized:
            for sensor in sensor_list:
                if sensor in self.channels:
                    try:
                        channel = self.channels[sensor]
                        voltage = channel.voltage
                        raw_value = channel.value
                        ppm = self._voltage_to_ppm(sensor, voltage)
                        resistance_ratio = self._calculate_resistance_ratio(voltage)
                        
                        readings[sensor] = {
                            'voltage': round(voltage, 3),
                            'raw': raw_value,
                            'ppm': round(ppm, 2),
                            'resistance_ratio': round(resistance_ratio, 3),
                            'timestamp': datetime.now().isoformat()
                        }
                        
                    except Exception as e:
                        print(f"Error reading {sensor}: {e}")
                        readings[sensor] = {
                            'voltage': 0,
                            'raw': 0,
                            'ppm': 0,
                            'error': str(e)
                        }
        else:
            # Simulation mode
            import random
            for sensor in sensor_list:
                readings[sensor] = {
                    'voltage': round(random.uniform(0.5, 3.0), 3),
                    'raw': random.randint(150, 900),
                    'ppm': round(random.uniform(10, 1000), 2),
                    'resistance_ratio': round(random.uniform(0.5, 3.0), 3),
                    'timestamp': datetime.now().isoformat()
                }
        
        return readings
    
    def read_all_data(self, sensor_list):
        """Read VOC sensors + environmental data together"""
        # Read environment first
        env_data = self.read_environment()
        
        # Read VOC sensors
        voc_data = self.read_sensors(sensor_list)
        
        # Combine
        return {
            'environment': env_data,
            'voc_sensors': voc_data,
            'timestamp': datetime.now().isoformat()
        }
    
    def start_priming(self):
        """Start sensor heating/priming"""
        if not self.is_heating:
            self.heating_start_time = time.time()
            self.is_heating = True
            print("VOC sensor priming started")
    
    def are_ready(self):
        """Check if sensors are ready"""
        if not self.is_heating or not self.heating_start_time:
            return False
        
        elapsed = time.time() - self.heating_start_time
        return elapsed >= self.HEATING_TIME
    
    def _voltage_to_ppm(self, sensor, voltage):
        """Convert voltage to PPM (placeholder - needs calibration)"""
        # This is a simplified conversion
        # Real implementation needs sensor-specific calibration curves
        return voltage * 100
    
    def _calculate_resistance_ratio(self, voltage):
        """Calculate Rs/R0 ratio"""
        if voltage <= 0:
            return 0
        # Simplified calculation
        return (self.VREF - voltage) / voltage
    
    def generate_csv(self, sensor_data):
        """Generate CSV file from sensor readings (including environment)"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"/tmp/sensor_data_{timestamp}.csv"
        
        try:
            with open(filename, 'w', newline='') as csvfile:
                # Check if environment data is present
                if 'environment' in sensor_data and 'voc_sensors' in sensor_data:
                    env = sensor_data['environment']
                    voc = sensor_data['voc_sensors']
                    
                    # Headers: Temperature, Humidity, then each VOC sensor
                    fieldnames = ['Temperature', 'Humidity'] + list(voc.keys())
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    # Data row
                    row = {
                        'Temperature': env['temperature'],
                        'Humidity': env['humidity']
                    }
                    row.update({sensor: data['ppm'] for sensor, data in voc.items()})
                    writer.writerow(row)
                else:
                    # Legacy format (just VOC sensors)
                    fieldnames = list(sensor_data.keys())
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    row = {sensor: data['ppm'] for sensor, data in sensor_data.items()}
                    writer.writerow(row)
            
            print(f"CSV generated: {filename}")
            return filename
            
        except Exception as e:
            print(f"Error generating CSV: {e}")
            return None
    
    def cleanup(self):
        """Cleanup resources"""
        self.is_heating = False
        self.channels.clear()
        self.mcp_chips.clear()
        
        if self.dht_device:
            try:
                self.dht_device.exit()
            except:
                pass
        
        print("Sensor manager cleaned up")
