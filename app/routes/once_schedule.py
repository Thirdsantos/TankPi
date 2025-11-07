import datetime
import pytz
import threading
from fastapi import APIRouter, Request
from run import aquarium
from app.services.motor import trigger_motor
from app.services.notify_service import notify_task_complete
from app.scheduler_instance import scheduler
import requests

# Create router instance
once_route = APIRouter()
aquarium_id = aquarium


@once_route.post(f"/{aquarium_id}/add_task")
async def add_one_time_task(request: Request):
    """
    Adds a one-time scheduled feeding/maintenance task using APScheduler.

    Expected JSON:
    {
        "aquarium_id": <int>,
        "cycle": <int>,
        "job_id": "schedule_at_YYYYMMDD_HHMMSS",
        "food": "flakes" | "pellet",
        "schedule_time": "2025-10-16 15:30:00"   <-- local time (Asia/Manila)
    }
    """
    try:
        data = await request.json()
        print("[ONCE-SCHEDULE] Received payload:", data)

        # Extract fields
        task_aquarium_id = data.get("aquarium_id")
        cycle = data.get("cycle")
        job_id = data.get("job_id")
        food_type = data.get("food_type") or data.get("food")
        run_time_str = data.get("run_time") or data.get("schedule_time")
        timezone_str = "Asia/Manila"  # ✅ Default timezone

        # ✅ Validation
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

        # ✅ Convert run_time to UTC
        try:
            local_tz = pytz.timezone(timezone_str)
            local_dt = local_tz.localize(datetime.datetime.strptime(run_time_str, "%Y-%m-%d %H:%M:%S"))
            utc_dt = local_dt.astimezone(pytz.utc)
        except Exception as e:
            print("[ONCE-SCHEDULE] ❌ Invalid datetime format or timezone:", e)
            return {"status": "error", "message": "Invalid datetime or timezone"}

        # ✅ Actual scheduled function
        def execute_feeding():
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[ONCE-SCHEDULE JOB] 🚀 Executing job {job_id} at {now}")

            try:
                # ✅ Trigger the physical motor
                trigger_motor(food_type, now, cycle)
                print(f"[ONCE-SCHEDULE JOB] ✅ Motor triggered ({cycle}x {food_type})")

                # ✅ Notify backend immediately when done
                url = f"https://aquacare-5cyr.onrender.com/task_complete/{job_id}"
                print(f"[ONCE-SCHEDULE JOB] 📢 Sending POST request to: {url}")

                response = requests.post(url, timeout=10)
                response.raise_for_status()

                print(f"[ONCE-SCHEDULE JOB] ✅ Successfully marked task {job_id} as complete.")
                return {"status": "success", "message": f"Task {job_id} marked complete."}

            except requests.exceptions.RequestException as e:
                print(f"[ONCE-SCHEDULE JOB ERROR] ❌ Failed to notify backend: {e}")
            except Exception as e:
                print(f"[ONCE-SCHEDULE JOB ERROR] ❌ Failed to execute feeding for {job_id}: {e}")

        # ✅ Add job to scheduler
        scheduler.add_job(
            execute_feeding,
            trigger="date",
            run_date=utc_dt,
            id=job_id,
            replace_existing=True
        )

        print(f"[ONCE-SCHEDULE] ✅ Task '{job_id}' scheduled at {run_time_str} ({timezone_str})")

        return {
            "status": "scheduled",
            "job_id": job_id,
            "run_time_local": run_time_str,
            "run_time_utc": utc_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "aquarium_id": aquarium_id,
            "cycle": cycle,
            "food_type": food_type,
        }

    except Exception as e:
        print(f"[ONCE-SCHEDULE ERROR] {e}")
        return {"status": "error", "message": str(e)}


@once_route.delete(f"/{aquarium_id}/delete_task")
async def delete_one_time_task(request: Request):
    """
    Deletes a scheduled APScheduler task by its job_id (document ID).

    Expected JSON:
    {
        "aquarium_id": <int>,
        "document_id": "schedule_at_YYYYMMDD_HHMMSS"
    }
    """
    try:
        data = await request.json()
        task_aquarium_id = data.get("aquarium_id")
        job_id = data.get("document_id")

        # ✅ Validate aquarium_id
        if task_aquarium_id != aquarium_id:
            print(f"[DELETE-SCHEDULE] ❌ Aquarium ID mismatch ({task_aquarium_id} != {aquarium_id})")
            return {"status": "error", "message": "Invalid aquarium_id"}

        if not job_id:
            print("[DELETE-SCHEDULE] ❌ Missing job_id in request.")
            return {"status": "error", "message": "Missing job_id"}

        # ✅ Try to remove job
        job = scheduler.get_job(job_id)
        if job:
            scheduler.remove_job(job_id)
            print(f"[DELETE-SCHEDULE] ✅ Job '{job_id}' successfully removed from scheduler.")
            return {
                "status": "deleted",
                "aquarium_id": aquarium_id,
                "job_id": job_id
            }
        else:
            print(f"[DELETE-SCHEDULE] ⚠️ No job found with id '{job_id}'.")
            return {
                "status": "not_found",
                "message": f"No job found with id '{job_id}'"
            }

    except Exception as e:
        print(f"[DELETE-SCHEDULE ERROR] {e}")
        return {"status": "error", "message": str(e)}
