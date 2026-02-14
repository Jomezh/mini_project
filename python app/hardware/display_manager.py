try:
    import RPi.GPIO as GPIO
    HAS_HARDWARE = True
except ImportError:
    HAS_HARDWARE = False
    print("Warning: GPIO libraries not available. Running in simulation mode.")

class DisplayManager:
    """Manages display backlight"""
    
    BACKLIGHT_PIN = 23  # GPIO 23 for backlight control
    
    def __init__(self):
        self.backlight_on = False
        
        if HAS_HARDWARE:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.BACKLIGHT_PIN, GPIO.OUT)
                print(f"Display backlight initialized on GPIO {self.BACKLIGHT_PIN}")
            except Exception as e:
                print(f"Failed to initialize backlight: {e}")
    
    def turn_on(self):
        """Turn backlight ON (GPIO 23 HIGH)"""
        if HAS_HARDWARE:
            GPIO.output(self.BACKLIGHT_PIN, GPIO.HIGH)
        self.backlight_on = True
        print("Display backlight ON")
    
    def turn_off(self):
        """Turn backlight OFF (GPIO 23 LOW)"""
        if HAS_HARDWARE:
            GPIO.output(self.BACKLIGHT_PIN, GPIO.LOW)
        self.backlight_on = False
        print("Display backlight OFF")
    
    def cleanup(self):
        """Cleanup GPIO"""
        if HAS_HARDWARE:
            self.turn_off()
            GPIO.cleanup(self.BACKLIGHT_PIN)
