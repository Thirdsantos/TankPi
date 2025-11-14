import datetime
import requests
from run import aquarium
from .motor import trigger_motor

aquarium_id = aquarium
BACKEND_URL = "https://aquacare-5cyr.onrender.com"

def get_backend_schedule():
    url = f"{BACKEND_URL}/get_schedules/{aquarium_id}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        global_enabled = data.get("enabled", True)
        schedules = data.get("schedules", [])
        print(f"[FEEDER] Schedules fetched: {schedules}")
        return global_enabled, schedules
    except Exception as e:
        print(f"[FEEDER ERROR] {e}")
        return True, []

def get_current_time():
    return datetime.datetime.now().strftime("%H:%M")

def trigger_feeder(source: str, time_str: str, cycle: int = 1, food: str = "pellet"):
    print(f"[FEEDER] Triggering {food} x{cycle} via {source} at {time_str}")
    motor_result = trigger_motor(food, time_str, cycle)
    return {"status": "success", "mode": source, "time": time_str, "cycle": cycle, "food": food, "motor_result": motor_result}

def handle_feeder_request(force_trigger: bool = False):
    current_time = get_current_time()
    global_enabled, schedules = get_backend_schedule()
    if not global_enabled and not force_trigger:
        return {"status": "off", "message": "Automatic feeding is OFF globally."}
    triggered = []
    for s in schedules:
        schedule_time = s.get("time")
        cycle = s.get("cycle", 1)
        food = s.get("food", "pellet").lower()
        if food == "pellets": food = "pellet"
        schedule_switch = s.get("switch", True)
        if force_trigger or (schedule_time == current_time and schedule_switch):
            triggered.append(trigger_feeder("schedule", schedule_time, cycle, food))
    if triggered:
        return {"status": "success", "triggers": triggered}
    return {"status": "pending", "backend_time": current_time, "message": "No scheduled feeding now."}

def check_and_trigger_schedule():
    current_time = get_current_time()
    global_enabled, schedules = get_backend_schedule()
    if not global_enabled:
        return None
    triggered = []
    for s in schedules:
        schedule_time = s.get("time")
        cycle = s.get("cycle", 1)
        food = s.get("food", "pellet").lower()
        if food == "pellets": food = "pellet"
        schedule_switch = s.get("switch", True)
        if schedule_time == current_time and schedule_switch:
            triggered.append(trigger_feeder("schedule-auto", current_time, cycle, food))
    if triggered:
        return {"status": "success", "triggers": triggered}
    return None
