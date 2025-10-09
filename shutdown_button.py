#!/usr/bin/env python3
# shutdown_button.py
# Button-controlled Bluetooth (short press to enable BLE Wi-Fi JSON), shutdown (>=10s)
# + Manual jog of ULN2003 stepper via GPIO13 (hold = move, release = stop)
# + Auto pause when motor is in use by FastAPI feeder (lock file detection)

import RPi.GPIO as GPIO
import time
import subprocess
import threading
import os
import ble_wifi_module  # Fixed BLE module

# -----------------------------
# GPIO Pin Configuration
# -----------------------------
BUTTON_PIN = 16        # BCM GPIO16 (shutdown / BLE button)
BUZZER_PIN = 19        # BCM GPIO19 (buzzer)
HOME_BUTTON_PIN = 13   # BCM GPIO13 (manual stepper jog button)

# Motor GPIO pins (ULN2003 inputs)
IN1 = 23
IN2 = 24
IN3 = 27
IN4 = 22

# -----------------------------
# Timing Settings
# -----------------------------
SHORT_MIN = 0.5
SHORT_MAX = 5.0
HOLD_SECONDS = 10.0
BEEP_DURATION = 1.0

# Lock file used to detect if motor is busy
LOCK_FILE = "/tmp/motor_busy.lock"

# -----------------------------
# GPIO Setup
# -----------------------------
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.setup(HOME_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

for pin in [IN1, IN2, IN3, IN4]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# -----------------------------
# Stepper Motor Sequence
# -----------------------------
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

# -----------------------------
# Utility Functions
# -----------------------------
def motor_busy():
    return os.path.exists(LOCK_FILE)

def beep(duration=0.2, count=1, gap=0.15):
    for _ in range(count):
        GPIO.output(BUZZER_PIN, True)
        time.sleep(duration)
        GPIO.output(BUZZER_PIN, False)
        time.sleep(gap)

def step_motor_jog(delay=0.002, direction=1):
    seq = STEP_SEQUENCE if direction == 1 else list(reversed(STEP_SEQUENCE))
    for s in seq:
        GPIO.output(IN1, s[0])
        GPIO.output(IN2, s[1])
        GPIO.output(IN3, s[2])
        GPIO.output(IN4, s[3])
        time.sleep(delay)

def release_motor():
    for pin in [IN1, IN2, IN3, IN4]:
        GPIO.output(pin, GPIO.LOW)

# -----------------------------
# BLE Functions
# -----------------------------
ble_started = False
def start_ble():
    global ble_started
    if ble_started:
        print("[BLE] Already started")
        return
    print("[BLE] Starting BLE server...")
    subprocess.call(['rfkill', 'unblock', 'bluetooth'])
    threading.Thread(target=ble_wifi_module.main, daemon=True).start()
    ble_started = True
    beep(0.2, count=2)
    print("[BLE] BLE server started and advertising")

# -----------------------------
# Main Loop
# -----------------------------
def main():
    print(f"Press button {SHORT_MIN}-{SHORT_MAX}s to start BLE. Hold >= {HOLD_SECONDS}s to shutdown.")
    try:
        while True:
            # Pause motor if feeder busy
            if motor_busy():
                release_motor()
                time.sleep(0.5)
                continue

            # Shutdown / BLE button
            if GPIO.input(BUTTON_PIN) == GPIO.LOW:
                start_time = time.time()
                while GPIO.input(BUTTON_PIN) == GPIO.LOW:
                    elapsed = time.time() - start_time
                    if elapsed >= HOLD_SECONDS:
                        print("[ACTION] Shutdown triggered.")
                        beep(BEEP_DURATION)
                        GPIO.output(BUZZER_PIN, False)
                        subprocess.call(['/sbin/shutdown', '-h', 'now'])
                        return
                    time.sleep(0.02)

                press_duration = time.time() - start_time
                if SHORT_MIN <= press_duration <= SHORT_MAX:
                    print(f"[ACTION] Short press ({press_duration:.2f}s) → start BLE")
                    start_ble()

            # Manual stepper jog
            if GPIO.input(HOME_BUTTON_PIN) == GPIO.LOW:
                while GPIO.input(HOME_BUTTON_PIN) == GPIO.LOW and not motor_busy():
                    step_motor_jog(delay=0.002)
                release_motor()
            else:
                release_motor()

            time.sleep(0.02)

    except KeyboardInterrupt:
        print("\n[EXIT] KeyboardInterrupt")
    finally:
        release_motor()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
