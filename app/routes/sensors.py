import sys
import time
import os
import requests

# Add root project directory to import path (adjust as needed)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Imports from your own modules
from run import aquarium  # this holds your aquarium ID
from sensor import read_sensors  # function to read real sensor data

def send_sensor_realtime():
    url = f"https://aquacare-5cyr.onrender.com/{aquarium}/sensors"
    sensor = read_sensors()  # fetch real data
    try:
        response = requests.post(url, json=sensor, timeout=5)
        print(f"[REALTIME] Sent: {sensor} | Status: {response.status_code}")
    except requests.RequestException as e:
        print(f"[REALTIME] Error: {e}")

def send_sensor_hourly():
    url = f"https://aquacare-5cyr.onrender.com/{aquarium}/hourly_log"
    sensor = read_sensors()  # fetch real data
    try:
        response = requests.post(url, json=sensor, timeout=5)
        print(f"[HOURLY] Sent: {sensor} | Status: {response.status_code}")
    except requests.RequestException as e:
        print(f"[HOURLY] Error: {e}")

if __name__ == "__main__":
    print("🚀 Starting continuous sensor data transmission...")

    minutes_passed = 0

    while True:
        send_sensor_realtime()

        # Send hourly data every 60 minutes
        minutes_passed += 1
        if minutes_passed >= 60:
            send_sensor_hourly()
            minutes_passed = 0

        time.sleep(1)
