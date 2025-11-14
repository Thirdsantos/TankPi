from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.services.motor import trigger_motor
import datetime
import threading
from run import aquarium  # <-- your configured aquarium ID

feed_route = APIRouter()

# Convert imported aquarium ID to string (safe for matching URL params)
aquarium_id_from_run = str(aquarium)

# Create a lock to prevent multiple simultaneous feeds
feed_lock = threading.Lock()


def validate_aquarium_id(aquarium_id: str):
    """Ensures URL aquarium_id matches the configured aquarium."""
    return str(aquarium_id) == aquarium_id_from_run


def get_current_time():
    """Helper to get current time in HH:MM:SS format."""
    return datetime.datetime.now().strftime("%H:%M:%S")


# -------------------------
# Request Models
# -------------------------
class FeedRequest(BaseModel):
    food: str  # expects "pellet" or "flakes"


class CycleFeedRequest(BaseModel):
    food: str  # expects "pellet" or "flakes"
    cycle: int  # expects positive integer


# -------------------------
# MANUAL HOLD FEED
# -------------------------
@feed_route.post("/aquarium/{aquarium_id}/manual/hold_feed")
def hold_feed(aquarium_id: str, feed: FeedRequest):

    # Validate aquarium ID
    if not validate_aquarium_id(aquarium_id):
        return JSONResponse(
            {"Message": f"Invalid aquarium_id '{aquarium_id}', expected '{aquarium_id_from_run}'"},
            status_code=400
        )

    # Prevent simultaneous feed operations
    if feed_lock.locked():
        return JSONResponse(
            {"Message": "Feeder is currently running, please wait until it finishes."},
            status_code=429
        )

    with feed_lock:
        try:
            food = feed.food.lower()
            if food not in ["pellet", "flakes"]:
                food = "flakes"

            print(f"Feeding {food}...")

            time_str = get_current_time()
            result = trigger_motor(food, time_str, cycle=1)

            print(f"Feeding complete: {food}")

            return JSONResponse({
                "Message": f"Fed {food} successfully for aquarium {aquarium_id}",
                "details": result
            })

        except Exception as e:
            return JSONResponse({"Message": str(e)}, status_code=500)


# -------------------------
# MANUAL CYCLE FEED
# -------------------------
@feed_route.post("/aquarium/{aquarium_id}/manual/cycle_feed")
def cycle_feed(aquarium_id: str, feed: CycleFeedRequest):

    # Validate aquarium ID
    if not validate_aquarium_id(aquarium_id):
        return JSONResponse(
            {"Message": f"Invalid aquarium_id '{aquarium_id}', expected '{aquarium_id_from_run}'"},
            status_code=400
        )

    # Prevent simultaneous feed operations
    if feed_lock.locked():
        return JSONResponse(
            {"Message": "Feeder is currently running, please wait until it finishes."},
            status_code=429
        )

    with feed_lock:
        try:
            food = feed.food.lower()
            if food not in ["pellet", "flakes"]:
                return JSONResponse(
                    {"Message": "Invalid food type. Use 'pellet' or 'flakes'."},
                    status_code=400
                )

            cycles = feed.cycle
            if not isinstance(cycles, int) or cycles <= 0:
                return JSONResponse(
                    {"Message": "Invalid cycle value. Must be a positive integer."},
                    status_code=400
                )

            print(f"Feeding {food} for {cycles} cycle(s)...")

            all_results = []
            for i in range(cycles):
                time_str = get_current_time()
                print(f"[Cycle {i+1}/{cycles}] Triggering {food} motor at {time_str}...")
                result = trigger_motor(food, time_str, cycle=1)
                all_results.append(result)

            print(f"Feeding complete: {food} ({cycles} cycle(s))")

            return JSONResponse({
                "Message": f"Fed {food} for {cycles} cycle(s) successfully for aquarium {aquarium_id}",
                "details": all_results
            })

        except Exception as e:
            return JSONResponse({"Message": str(e)}, status_code=500)
