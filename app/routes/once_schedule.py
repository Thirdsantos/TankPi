import datetime
from fastapi import APIRouter, Request
from run import aquarium
from app.services.motor import trigger_motor  # ✅ correct import

# Create router instance
once_route = APIRouter()
aquarium_id = aquarium


@once_route.post(f"/{aquarium_id}/add_task")
async def add_one_time_task(request: Request):
    """
    Receive a one-time feeding/maintenance command from the backend.

    Expected JSON:
    {
        "aquarium_id": <int>,
        "cycle": <int>,
        "food_type": "flakes" | "pellet",
        "job_id": "schedule_at_YYYYMMDD_HHMMSS"
    }

    - Validates aquarium_id
    - Validates cycle and food_type
    - Runs feeder motor
    - Returns execution result
    """
    try:
        data = await request.json()
        print("[ONCE-SCHEDULE] Received payload:", data)

        task_aquarium_id = data.get("aquarium_id")
        cycle = data.get("cycle")
        job_id = data.get("job_id")
        food_type = data.get("food_type")

        # Validation
        if task_aquarium_id != aquarium_id:
            print(f"[ONCE-SCHEDULE] ❌ Aquarium ID mismatch ({task_aquarium_id} != {aquarium_id})")
            return {"status": "error", "message": "Invalid aquarium_id"}

        if not isinstance(cycle, int) or cycle <= 0:
            print("[ONCE-SCHEDULE] ❌ Invalid cycle value")
            return {"status": "error", "message": "Invalid cycle value"}

        valid_food_types = ["flakes", "pellet"]
        if food_type not in valid_food_types:
            print(f"[ONCE-SCHEDULE] ❌ Invalid food_type '{food_type}'")
            return {
                "status": "error",
                "message": f"Invalid food_type. Must be one of: {valid_food_types}"
            }

        # Execute motor
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        motor_result = trigger_motor(food_type, now, cycle)
        print(f"[ONCE-SCHEDULE] ✅ Motor triggered for {cycle} cycles of {food_type} at {now}")

        # Respond to backend (backend will mark Firestore status=done)
        return {
            "status": "success",
            "aquarium_id": aquarium_id,
            "cycle": cycle,
            "food_type": food_type,
            "job_id": job_id,
            "motor_result": motor_result,
            "executed_at": now
        }

    except Exception as e:
        print(f"[ONCE-SCHEDULE ERROR] {e}")
        return {"status": "error", "message": str(e)}
