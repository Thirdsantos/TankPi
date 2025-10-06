import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from w1thermsensor import W1ThermSensor
from RPLCD.i2c import CharLCD

# I2C and ADS1115 setup
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c, address=0x48)

ph_sensor = AnalogIn(ads, ADS.P1)
turbidity_channel = AnalogIn(ads, ADS.P0)
temp_sensor = W1ThermSensor()
calibration_value = 21.34 - 0.7

# LCD setup
lcd = CharLCD('PCF8574', 0x27, cols=20, rows=4)

def voltage_to_ph(ph_voltage):
    ph_value = -5.70 * ph_voltage + calibration_value
    return round(ph_value, 1)

def voltage_to_turbidity(voltage, vref=5.0):
    sensor_value = (voltage / vref) * 1023
    turbidity = 100 * (1 - (sensor_value / 640))
    return max(0.0, round(turbidity, 1))

def read_sensors(update_lcd: bool = True):
    """
    Reads the sensors and optionally updates the LCD.
    - update_lcd=True → write readings to LCD
    - update_lcd=False → just return readings
    """
    ph_voltage = ph_sensor.voltage
    temperature_c = temp_sensor.get_temperature()
    turbidity_voltage = turbidity_channel.voltage

    data = {
        "ph": voltage_to_ph(ph_voltage),
        "temperature": int(temperature_c),
        "turbidity": int(voltage_to_turbidity(turbidity_voltage))
    }

    if update_lcd:
        # Update LCD
        lcd.cursor_pos = (0, 0)
        lcd.write_string(f"pH: {data['ph']:<6}")

        lcd.cursor_pos = (1, 0)
        lcd.write_string(f"Temp: {data['temperature']}C   ")

        lcd.cursor_pos = (2, 0)
        lcd.write_string(f"Turb: {data['turbidity']}  ")

        lcd.cursor_pos = (3, 0)
        lcd.write_string("Monitoring...     ")

    return data
