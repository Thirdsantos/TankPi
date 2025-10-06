# app/routes/manual_feed.py
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.services.motor import trigger_motor
import datetime
import threading

feed_route = APIRouter()

# Create a lock to prevent multiple simultaneous feeds
feed_lock = threading.Lock()

def get_current_time():
    """Helper to get current time in HH:MM:SS format."""
    return datetime.datetime.now().strftime("%H:%M:%S")

class FeedRequest(BaseModel):
    food: str  # expects "pellet" or "flakes"

@feed_route.post("/aquarium/{aquarium_id}/feed")
def manual_feed(aquarium_id: int, feed: FeedRequest):
    """
    Manual feed route for a specific aquarium.
    Ensures only one feed operation runs at a time.
    """
    if feed_lock.locked():
        # If already feeding, reject the request
        return JSONResponse(
            {"Message": "Feeder is currently running, please wait until it finishes."},
            status_code=429  # Too Many Requests
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
