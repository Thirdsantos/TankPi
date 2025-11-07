import datetime
import time
import RPi.GPIO as GPIO
import os
import atexit

# GPIO pins for ULN2003 + 28BYJ-48
IN1, IN2, IN3, IN4 = 23, 24, 27, 22

# 8-step half-step sequence
STEP_SEQUENCE = [
    [1, 0, 0, 0],
    [1, 1, 0, 0],
    [0, 1, 0, 0],
    [0, 1, 1, 0],
    [0, 0, 1, 0],
    [0, 0, 1, 1],
    [0, 0, 0, 1],
    [1, 0, 0, 1]
]

LOCK_FILE = "/tmp/motor_busy.lock"

STEPS_PER_FULL_ROTATION = 512  # One full revolution (half-stepping)
STEP_DELAY = 0.001              # Delay between steps (lower = faster, but less torque)

# -------------------- GPIO SETUP --------------------

def setup_gpio():
    """Initialize GPIO pins."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pin in [IN1, IN2, IN3, IN4]:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, 0)

def release_motor():
    """Turn off all coils."""
    for pin in [IN1, IN2, IN3, IN4]:
        GPIO.output(pin, 0)
    time.sleep(0.05)

def cleanup_gpio():
    """Release motor and cleanup GPIO pins safely."""
    try:
        release_motor()
        GPIO.cleanup()
    except Exception:
        pass

# Ensure cleanup always runs when app exits
atexit.register(cleanup_gpio)

# -------------------- CORE MOTOR LOGIC --------------------

def step_motor(steps=STEPS_PER_FULL_ROTATION, delay=STEP_DELAY, direction=1):
    """Rotate motor by given number of steps."""
    seq = STEP_SEQUENCE if direction == 1 else list(reversed(STEP_SEQUENCE))
    for _ in range(steps):
        for s in seq:
            GPIO.output(IN1, s[0])
            GPIO.output(IN2, s[1])
            GPIO.output(IN3, s[2])
            GPIO.output(IN4, s[3])
            time.sleep(delay)

def wait_for_lock_release(timeout=30):
    """Wait until no other motor job is running."""
    start = time.time()
    while os.path.exists(LOCK_FILE):
        # Remove stale lock files older than 60 seconds
        if time.time() - os.path.getmtime(LOCK_FILE) > 60:
            print("[MOTOR] ⚠️ Stale lock detected. Removing...")
            os.remove(LOCK_FILE)
            break

        if time.time() - start > timeout:
            print("[MOTOR] ⚠️ Timeout waiting for lock. Forcing unlock.")
            os.remove(LOCK_FILE)
            break

        time.sleep(0.2)

# -------------------- MOTOR ACTIONS --------------------

def pellet_motor(time_str: str, cycle: int = 1):
    """Pellet feeder motor (clockwise)."""
    wait_for_lock_release()
    open(LOCK_FILE, "w").close()
    print(f"[MOTOR] Pellet start — {time_str}")

    try:
        for i in range(cycle):
            print(f"[MOTOR] Pellet (CW) — cycle {i+1}/{cycle}")
            step_motor(direction=1)
            time.sleep(0.1)
    finally:
        cleanup_gpio()
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
        print(f"[MOTOR] Pellet done — {time_str}")

    return {"status": "success", "motor": "pellet", "time": time_str, "cycle": cycle}


def flakes_motor(time_str: str, cycle: int = 1):
    """Flakes feeder motor (counterclockwise)."""
    wait_for_lock_release()
    open(LOCK_FILE, "w").close()
    print(f"[MOTOR] Flakes start — {time_str}")

    try:
        for i in range(cycle):
            print(f"[MOTOR] Flakes (CCW) — cycle {i+1}/{cycle}")
            step_motor(direction=-1)
            time.sleep(0.1)
    finally:
        cleanup_gpio()
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
        print(f"[MOTOR] Flakes done — {time_str}")

    return {"status": "success", "motor": "flakes", "time": time_str, "cycle": cycle}


def trigger_motor(food: str, time_str: str, cycle: int = 1):
    """Dispatch correct motor based on food type."""
    setup_gpio()  # Ensure GPIO is ready before motor run

    if food.lower() == "pellet":
        return pellet_motor(time_str, cycle)
    elif food.lower() == "flakes":
        return flakes_motor(time_str, cycle)
    else:
        print(f"[MOTOR] ❌ Invalid food type: {food}")
        return {"status": "error", "message": "Invalid food type"}
