import datetime
import time
import RPi.GPIO as GPIO
import os

# GPIO pins for ULN2003 + 28BYJ-48
IN1, IN2, IN3, IN4 = 23, 24, 27, 22

# 8-step half-step sequence
STEP_SEQUENCE = [
    [1,0,0,0],
    [1,1,0,0],
    [0,1,0,0],
    [0,1,1,0],
    [0,0,1,0],
    [0,0,1,1],
    [0,0,0,1],
    [1,0,0,1]
]

LOCK_FILE = "/tmp/motor_busy.lock"

# One output revolution = ~512 half-steps
STEPS_PER_FULL_ROTATION = 512
STEP_DELAY = 0.001  # fast but reliable

def setup_gpio():
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

def step_motor(steps=STEPS_PER_FULL_ROTATION, delay=STEP_DELAY, direction=1):
    """Rotate motor by a given number of steps and direction."""
    seq = STEP_SEQUENCE if direction == 1 else list(reversed(STEP_SEQUENCE))
    for _ in range(steps):
        for s in seq:
            GPIO.output(IN1, s[0])
            GPIO.output(IN2, s[1])
            GPIO.output(IN3, s[2])
            GPIO.output(IN4, s[3])
            time.sleep(delay)

def wait_for_lock_release(timeout=30):
    """Ensure only one motor runs at a time."""
    start = time.time()
    while os.path.exists(LOCK_FILE):
        if time.time() - start > timeout:
            break
        time.sleep(0.2)

def pellet_motor(time_str: str, cycle: int = 1):
    """Pellet feeder motor (clockwise)."""
    wait_for_lock_release()
    open(LOCK_FILE, "w").close()
    setup_gpio()
    try:
        for i in range(cycle):
            print(f"[MOTOR] Pellet (CW) — {time_str} (cycle {i+1}/{cycle})")
            step_motor(direction=1)  # CW
            time.sleep(0.2)
    finally:
        release_motor()
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    return {"status": "success", "motor": "pellet", "time": time_str, "cycle": cycle}

def flakes_motor(time_str: str, cycle: int = 1):
    """Flakes feeder motor (counterclockwise)."""
    wait_for_lock_release()
    open(LOCK_FILE, "w").close()
    setup_gpio()
    try:
        for i in range(cycle):
            print(f"[MOTOR] Flakes (CCW) — {time_str} (cycle {i+1}/{cycle})")
            step_motor(direction=-1)  # CCW
            time.sleep(0.2)
    finally:
        release_motor()
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    return {"status": "success", "motor": "flakes", "time": time_str, "cycle": cycle}

def trigger_motor(food: str, time_str: str, cycle: int = 1):
    """Dispatch motor control based on food type."""
    if food.lower() == "pellet":
        return pellet_motor(time_str, cycle)
    else:
        return flakes_motor(time_str, cycle)
