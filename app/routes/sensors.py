import requests
from app.services.sensor import read_sensors
from run import aquarium  # aquarium = 1 stays in run.py

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
