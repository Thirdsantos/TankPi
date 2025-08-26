import requests
from run import aquarium

def send_sensor_realtime():
  url = f"https://aquacare-5cyr.onrender.com/{aquarium}/sensors"

  sensor = {"ph" : 1, "temperature" : 1, "turbidity" : 1}
  response = requests.post(url,json = sensor)
  print(response.status_code)

def send_sensor_hourly():
  url = f"https://aquacare-5cyr.onrender.com/{aquarium}/hourly_log"
 
  sensor = {"ph" : 1, "temperature" : 1, "turbidity" : 1}
  response = requests.post(url, json = sensor)
  print(response.status_code)
