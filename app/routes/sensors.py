import requests
from app.services.sensor import read_sensors
from run import aquarium  # aquarium = 1 stays in run.py

previous_realtime = None


def send_sensor_realtime():
    global previous_realtime
    url = f"https://aquacare-5cyr.onrender.com/{aquarium}/sensors"
    sensor = read_sensors()

    # Only send if data has changed
    if sensor != previous_realtime:
        try:
            response = requests.post(url, json=sensor, timeout=5)
            print(f"[REALTIME] Sent: {sensor} | Status: {response.status_code}")
            previous_realtime = sensor  # update previous reading
        except requests.RequestException as e:
            print(f"[REALTIME] Error: {e}")
    else:
        print("[REALTIME] No change, skipping send.")

def send_sensor_hourly():
    url = f"https://aquacare-5cyr.onrender.com/{aquarium}/hourly_log"
    sensor = read_sensors()
    try:
        response = requests.post(url, json=sensor, timeout=5)
        print(f"[HOURLY] Sent: {sensor} | Status: {response.status_code}")
    except requests.RequestException as e:
        print(f"[HOURLY] Error: {e}")
