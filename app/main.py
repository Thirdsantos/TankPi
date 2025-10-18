from run import aquarium
import pytz
import requests
import datetime 


aquarium_id = aquarium

print("DEBUG: starting main.py")

from fastapi import FastAPI
print("DEBUG: imported FastAPI")

from fastapi.middleware.cors import CORSMiddleware
print("DEBUG: imported CORSMiddleware")

from apscheduler.schedulers.background import BackgroundScheduler
print("DEBUG: imported APScheduler")

# Import your routes AFTER FastAPI setup
from app.routes import video, feeder, manual_feed, once_schedule
print("DEBUG: imported routes")

from app.services.feeder_service import check_and_trigger_schedule
print("DEBUG: imported feeder_service")

from app.routes.sensors import send_sensor_realtime, send_sensor_hourly
print("DEBUG: imported sensors")

# ✅ Create FastAPI app
app = FastAPI()
print("DEBUG: FastAPI app created")

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
print("DEBUG: middleware added")

# ✅ Include routers — only after app is defined
app.include_router(video.video_route)
print("DEBUG: video router included")

app.include_router(manual_feed.feed_route)
print("DEBUG: manual_feed router included")

app.include_router(feeder.feeder_route)
print("DEBUG: feeder router included")

app.include_router(once_schedule.once_route)
print("DEBUG: once_schedule router included")

# ✅ Root endpoint
@app.get("/")
def root():
    return {"message": "FastAPI is running!"}
print("DEBUG: root endpoint added")

# ✅ Scheduler setup
scheduler = BackgroundScheduler()
print("DEBUG: scheduler created")

def auto_reschedule_all(aquarium_id: int):
    """
    Fetches all pending schedules from the backend and re-adds them to APScheduler.
    Prevents duplicates and uses document_id as job_id.
    """
    try:
        url = f"https://aquacare-5cyr.onrender.com/get_pending/{aquarium_id}"
        print(f"[AUTO-RESCHEDULER] Fetching pending schedules from: {url}")

        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        pending_tasks = data.get("pending_aquariums", [])
        if not pending_tasks:
            print(f"[AUTO-RESCHEDULER] No pending tasks found for aquarium {aquarium_id}")
            return {"status": "no_pending_tasks"}

        timezone_str = "Asia/Manila"
        local_tz = pytz.timezone(timezone_str)

        # Get all existing job IDs
        existing_job_ids = {job.id for job in scheduler.get_jobs()}

        for task in pending_tasks:
            job_id = task.get("document_id")
            food_type = task.get("food", "pellet")
            cycle = task.get("cycle", 1)
            schedule_time = task.get("schedule_time")

            if not job_id:
                print(f"[AUTO-RESCHEDULER] ⚠️ Skipping task with missing document_id: {task}")
                continue

            # Convert local Manila time to UTC
            try:
                local_dt = local_tz.localize(datetime.datetime.strptime(schedule_time, "%Y-%m-%d %H:%M:%S"))
                utc_dt = local_dt.astimezone(pytz.utc)
            except Exception as e:
                print(f"[AUTO-RESCHEDULER] ❌ Invalid datetime '{schedule_time}' for job {job_id}: {e}")
                continue

            # ✅ Skip if already scheduled with the same ID
            if job_id in existing_job_ids:
                print(f"[AUTO-RESCHEDULER] ⏩ Skipping duplicate job '{job_id}' (already scheduled)")
                continue

            # Define feeding job
            def execute_feeding(job_id=job_id, food_type=food_type, cycle=cycle):
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[AUTO-RESCHEDULER JOB] Executing job {job_id} at {now}")
                trigger_motor(food_type, now, cycle)
                print(f"[AUTO-RESCHEDULER JOB] ✅ Motor triggered ({cycle}x {food_type})")

            # ✅ Schedule job with document_id as the job ID
            scheduler.add_job(
                execute_feeding, #RAND!!! itong execute_feeding is dummy lang, 
                trigger="date", #hindi ko alam kung ano yung function na dapat tawagin kapag ka mag rurun na yung schedule
                run_date=utc_dt, #Ikaw mag lagay tapos tanggalin mo yang execute_feeding
                id=job_id,
                replace_existing=True
            )

            print(f"[AUTO-RESCHEDULER] ✅ Job '{job_id}' scheduled at {schedule_time} ({timezone_str})")

        print(f"[AUTO-RESCHEDULER] ✅ All tasks for aquarium {aquarium_id} processed.")
        return {"status": "success", "scheduled_count": len(pending_tasks)}

    except requests.exceptions.RequestException as e:
        print(f"[AUTO-RESCHEDULER ERROR] Failed to fetch data from server: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        print(f"[AUTO-RESCHEDULER ERROR] {e}")
        return {"status": "error", "message": str(e)}


@app.on_event("startup")
def on_startup():
    print("DEBUG: startup event running")
    scheduler.add_job(check_and_trigger_schedule, "interval", minutes=1)
    scheduler.add_job(send_sensor_realtime, "interval", seconds=3)
    scheduler.add_job(send_sensor_hourly, "interval", hours=1)
    scheduler.start()
    print("DEBUG: scheduler started")

    try:

        print(f"[STARTUP] Auto-rescheduling all tasks for aquarium {aquarium_id}...")
        result = auto_reschedule_all(aquarium_id)
        print(f"[STARTUP] Auto-rescheduler result: {result}")
    except Exception as e:
        print(f"[STARTUP ERROR] Failed to auto-reschedule: {e}")

@app.on_event("shutdown")
def on_shutdown():
    if scheduler.running:
        scheduler.shutdown()
    print("🛑 Scheduler stopped")
