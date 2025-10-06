import datetime
import time
import RPi.GPIO as GPIO

# Motor GPIO pins (ULN2003 inputs)
IN1 = 23
IN2 = 24
IN3 = 27
IN4 = 22

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(IN1, GPIO.OUT)
GPIO.setup(IN2, GPIO.OUT)
GPIO.setup(IN3, GPIO.OUT)
GPIO.setup(IN4, GPIO.OUT)

# Half-step sequence for 28BYJ-48 stepper motor
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

def get_current_time():
    """Helper to get current time for motor logs."""
    return datetime.datetime.now().strftime("%H:%M:%S")

def step_motor(steps=100, delay=0.002, direction=1):
    """
    Run the stepper motor for a number of steps.
    steps: number of steps
    delay: speed (lower = faster)
    direction: 1 = forward, -1 = backward
    """
    sequence = STEP_SEQUENCE if direction == 1 else list(reversed(STEP_SEQUENCE))
    for _ in range(steps):
        for seq in sequence:
            GPIO.output(IN1, seq[0])
            GPIO.output(IN2, seq[1])
            GPIO.output(IN3, seq[2])
            GPIO.output(IN4, seq[3])
            time.sleep(delay)

def pellet_motor(time_str: str, cycle: int = 1):
    """Run motor for pellet food: -160 steps then +160 steps."""
    for i in range(cycle):
        print(f"[MOTOR] Pellet motor activated at {time_str} (cycle {i+1}/{cycle}) [real-time: {get_current_time()}]")
        step_motor(steps=160, direction=-1)  # backward
        step_motor(steps=160, direction=1)   # forward
    return {
        "status": "success",
        "motor": "pellet",
        "time": time_str,
        "cycle": cycle,
        "message": f"Pellet motor ran at {time_str}, {cycle} times."
    }

def flakes_motor(time_str: str, cycle: int = 1):
    """Run motor for flakes food: +160 steps then -160 steps."""
    for i in range(cycle):
        print(f"[MOTOR] Flakes motor activated at {time_str} (cycle {i+1}/{cycle}) [real-time: {get_current_time()}]")
        step_motor(steps=160, direction=1)   # forward
        step_motor(steps=160, direction=-1)  # backward
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

def cleanup():
    """Release GPIO when done."""
    GPIO.output(IN1, 0)
    GPIO.output(IN2, 0)
    GPIO.output(IN3, 0)
    GPIO.output(IN4, 0)
    GPIO.cleanup()

# -------------------------
# TEST SCRIPT
# -------------------------
if __name__ == "__main__":
    try:
        print("🔧 Testing Flakes motor...")
        flakes_motor(get_current_time(), cycle=1)
        time.sleep(2)

        print("🔧 Testing Pellet motor...")
        pellet_motor(get_current_time(), cycle=1)
        time.sleep(2)

        print("✅ Test complete")
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted by user")
    finally:
        cleanup()
        print("GPIO cleaned up")
