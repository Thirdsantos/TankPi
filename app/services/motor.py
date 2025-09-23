# motor.py
import datetime
import time

def get_current_time():
    """Helper to get current time for motor logs."""
    return datetime.datetime.now().strftime("%H:%M:%S")


def pellet_motor(time_str: str, cycle: int = 1):
    """Run motor for pellet food, printing each cycle."""
    for i in range(cycle):
        print(f"[MOTOR] Pellet motor activated at {time_str} (cycle {i+1}/{cycle}) [real-time: {get_current_time()}]")
        time.sleep(1)  # simulate motor running for 1 second per cycle
    return {
        "status": "success",
        "motor": "pellet",
        "time": time_str,
        "cycle": cycle,
        "message": f"Pellet motor ran at {time_str}, {cycle} times."
    }


def flakes_motor(time_str: str, cycle: int = 1):
    """Run motor for flakes food, printing each cycle."""
    for i in range(cycle):
        print(f"[MOTOR] Flakes motor activated at {time_str} (cycle {i+1}/{cycle}) [real-time: {get_current_time()}]")
        time.sleep(1)  # simulate motor running for 1 second per cycle
    return {
        "status": "success",
        "motor": "flakes",
        "time": time_str,
        "cycle": cycle,
        "message": f"Flakes motor ran at {time_str}, {cycle} times."
    }


def trigger_motor(food: str, time_str: str, cycle: int = 1):
    """Decide which motor to activate based on food type."""
    cycle = int(cycle)
    if food.lower() == "pellet":
        return pellet_motor(time_str, cycle)
    else:
        return flakes_motor(time_str, cycle)
