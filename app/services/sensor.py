# sensor.py

import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from w1thermsensor import W1ThermSensor

# I2C and ADS1115 setup
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c, address=0x48)

ph_sensor = AnalogIn(ads, ADS.P1)
turbidity_channel = AnalogIn(ads, ADS.P0)
temp_sensor = W1ThermSensor()

def voltage_to_ph(ph_voltage):
    return round(7 + ((ph_voltage - 2.5) / 0.167), 2)

def voltage_to_turbidity(voltage):
    turbidity = 100 - ((voltage / 5.0) * 100)
    return max(0, min(100, turbidity))

def read_sensors():
    ph_voltage = ph_sensor.voltage
    temperature_c = temp_sensor.get_temperature()
    turbidity_voltage = turbidity_channel.voltage

    return {
        "ph": voltage_to_ph(ph_voltage),
        "temperature": int(temperature_c),
        "turbidity": int(voltage_to_turbidity(turbidity_voltage))
    }

