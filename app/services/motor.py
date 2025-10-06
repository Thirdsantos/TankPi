import datetime
import time
import RPi.GPIO as GPIO
import os

# Motor pins
IN1 = 23
IN2 = 24
IN3 = 27
IN4 = 22

# Half-step sequence for 28BYJ-48
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

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for pin in [IN1, IN2, IN3, IN4]:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, 0)

def release_motor():
    for pin in [IN1, IN2, IN3, IN4]:
        GPIO.output(pin, 0)
    time.sleep(0.05)

def get_current_time():
    return datetime.datetime.now().strftime("%H:%M:%S")

def step_motor(steps=100, delay=0.002, direction=1):
    sequence = STEP_SEQUENCE if direction == 1 else list(reversed(STEP_SEQUENCE))
    for _ in range(steps):
        for seq in sequence:
            GPIO.output(IN1, seq[0])
            GPIO.output(IN2, seq[1])
            GPIO.output(IN3, seq[2])
            GPIO.output(IN4, seq[3])
            time.sleep(delay)

def wait_for_lock_release(timeout=30):
    start = time.time()
    while os.path.exists(LOCK_FILE):
        if time.time() - start > timeout:
            break
        time.sleep(0.2)

def pellet_motor(time_str: str, cycle: int = 1):
    wait_for_lock_release()
    open(LOCK_FILE, "w").close()
    setup_gpio()
    try:
        for i in range(cycle):
            print(f"[MOTOR] Pellet motor activated at {time_str} (cycle {i+1}/{cycle})")
            step_motor(steps=160, direction=-1)
            step_motor(steps=160, direction=1)
    finally:
        release_motor()
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    return {"status": "success", "motor": "pellet", "time": time_str, "cycle": cycle}

def flakes_motor(time_str: str, cycle: int = 1):
    wait_for_lock_release()
    open(LOCK_FILE, "w").close()
    setup_gpio()
    try:
        for i in range(cycle):
            print(f"[MOTOR] Flakes motor activated at {time_str} (cycle {i+1}/{cycle})")
            step_motor(steps=160, direction=1)
            step_motor(steps=160, direction=-1)
    finally:
        release_motor()
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    return {"status": "success", "motor": "flakes", "time": time_str, "cycle": cycle}

def trigger_motor(food: str, time_str: str, cycle: int = 1):
    if food.lower() == "pellet":
        return pellet_motor(time_str, cycle)
    else:
        return flakes_motor(time_str, cycle)
