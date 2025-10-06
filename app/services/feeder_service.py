import datetime
import requests
from run import aquarium
from .motor import trigger_motor  # relative import for motor
from .db import init_db, save_schedules, get_schedules

# Initialize local DB
init_db()

aquarium_id = aquarium
BACKEND_URL = "https://aquacare-5cyr.onrender.com"


def get_backend_schedule():
    """Fetch global switch and feeding schedules from backend API, fallback to local DB."""
    url = f"{BACKEND_URL}/get_schedules/{aquarium_id}"
    try:
        response = requests.get(url, timeout=5)
        print("[DEBUG] Backend raw response:", response.text)
        if response.status_code == 200:
            data = response.json()
            print("[DEBUG] Backend parsed JSON:", data)
            global_enabled = data.get("enabled", True)
            schedules = data.get("schedules", [])
            # ✅ Save schedules to local DB for offline use
            save_schedules(schedules)
            return global_enabled, schedules
        else:
            print(f"[SCHEDULE] Failed to fetch, status={response.status_code}")
    except requests.RequestException as e:
        print(f"[SCHEDULE] Error: {e}")

    # ⬇️ If backend is unreachable, use local DB schedules
    print("[SCHEDULE] Using local database schedules")
    schedules = get_schedules()
    return True, schedules


def get_current_time():
    """Get current time in HH:MM format."""
    return datetime.datetime.now().strftime("%H:%M")


def trigger_feeder(source: str, time_str: str, cycle: int = None, food: str = None):
    """Trigger the feeder and run the appropriate motor."""
    if cycle is None:
        print(f"[FEEDER WARNING] No cycle specified for feeding at {time_str}")
        return {
            "status": "error",
            "mode": source,
            "time": time_str,
            "cycle": None,
            "food": food,
            "message": "No cycle specified, feeder not triggered."
        }

    motor_result = None
    if food:
        motor_result = trigger_motor(food, time_str, cycle)

    print(f"[FEEDER] {food if food else 'default'} dispensed by {source} at {time_str} "
          f"(total cycles: {cycle})")

    return {
        "status": "success",
        "mode": source,
        "time": time_str,
        "cycle": cycle,
        "food": food,
        "motor_result": motor_result,
        "message": f"Feeder triggered via {source} at {time_str}, {cycle} times. Food: {food if food else 'default'}"
    }


def handle_feeder_request(force_trigger: bool = False):
    """Handle a feeder request based on current time and backend/local schedules."""
    current_time = get_current_time()
    global_enabled, schedules = get_backend_schedule()

    if not global_enabled and not force_trigger:
        return {
            "status": "off",
            "mode": "schedule",
            "message": "Automatic feeding is OFF globally."
        }

    triggered = []
    for s in schedules:
        schedule_time = s.get("time")
        schedule_switch = s.get("switch", True)
        cycle = s.get("cycle")  # could be None
        food = s.get("food", "default")

        if force_trigger or (schedule_time == current_time and schedule_switch):
            result = trigger_feeder("schedule", schedule_time, cycle, food)
            triggered.append(result)

    if triggered:
        return {"status": "success", "triggers": triggered}
    else:
        return {
            "status": "pending",
            "mode": "schedule",
            "backend_time": current_time,
            "next_feed": schedules,
            "message": "No scheduled feeding at this time."
        }


def check_and_trigger_schedule():
    """Automatic check for scheduled feeding. Called every minute."""
    current_time = get_current_time()
    global_enabled, schedules = get_backend_schedule()

    if not global_enabled:
        print("[FEEDER] Global switch is OFF — skipping.")
        return None

    for s in schedules:
        schedule_time = s.get("time")
        cycle = s.get("cycle")  # could be None
        food = s.get("food", "default")
        schedule_switch = s.get("switch", True)

        if schedule_time == current_time and schedule_switch:
            return trigger_feeder("schedule-auto", current_time, cycle, food)

    return None