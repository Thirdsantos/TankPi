from run import aquarium
import requests

def send_sensor_realtime():
    url = f"https://aquacare-5cyr.onrender.com/{aquarium}/sensors"
    sensor = {"ph": 1, "temperature": 1, "turbidity": 1} # palitan toh, use a differnt py file para kunin yung sensor
                                                         # tapos i import dito then yun yung ibabato 
    try:
        response = requests.post(url, json=sensor, timeout=2)
        print(f"Received: {response.status_code}")
    except requests.RequestException as e:
        print(f"Error sending realtime sensor: {e}")


def send_sensor_hourly():
    url = f"https://aquacare-5cyr.onrender.com/{aquarium}/hourly_log"
    sensor = {"ph": 1, "temperature": 1, "turbidity": 1}
    try:
        response = requests.post(url, json=sensor, timeout=2)
        print(f"Received: {response.status_code}")
    except requests.RequestException as e:
        print(f"Error sending hourly sensor: {e}")