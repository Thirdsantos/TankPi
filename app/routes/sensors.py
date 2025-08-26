from run import aquarium  # this holds your aquarium ID
# from sensor import read_sensors  # function to read real sensor data
import requests

def send_sensor_realtime():
    url = f"https://aquacare-5cyr.onrender.com/{aquarium}/sensors"
    sensor = {"ph": 1, "temperature" : 1, "turbidity" : 1}  # fetch real data
    try:
        response = requests.post(url, json=sensor, timeout=5)
        print(f"[REALTIME] Sent: {sensor} | Status: {response.status_code}")
    except requests.RequestException as e:
        print(f"[REALTIME] Error: {e}")

def send_sensor_hourly():
    url = f"https://aquacare-5cyr.onrender.com/{aquarium}/hourly_log"
    sensor =  {"ph": 1, "temperature" : 1, "turbidity" : 1} # fetch real data
    try:
        response = requests.post(url, json=sensor, timeout=5)
        print(f"[HOURLY] Sent: {sensor} | Status: {response.status_code}")
    except requests.RequestException as e:
        print(f"[HOURLY] Error: {e}")

