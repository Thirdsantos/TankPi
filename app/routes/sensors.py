import sys
import os

# Add project root to sys.path so 'app' can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

import time
import requests

from app.services.sensor import read_sensors
from run import aquarium  # make sure 'run.py' is also importable from root

def send_sensor_realtime():
    url = f"https://aquacare-5cyr.onrender.com/{aquarium}/sensors"
    sensor = read_sensors()
    try:
        response = requests.post(url, json=sensor, timeout=5)
        print(f"[REALTIME] Sent: {sensor} | Status: {response.status_code}")
    except requests.RequestException as e:
        print(f"[REALTIME] Error: {e}")

def send_sensor_hourly():
    url = f"https://aquacare-5cyr.onrender.com/{aquarium}/hourly_log"
    sensor = read_sensors()
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

        minutes_passed += 1
        if minutes_passed >= 60:
            send_sensor_hourly()
            minutes_passed = 0

        time.sleep(1)
